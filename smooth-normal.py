# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
import math
import mathutils
import copy
import bmesh
from bpy.props import *

bl_info = {
    "name" : "Normal Smooth Tool",             
    "author" : "dskjal",                  
    "version" : (4,2),                  
    "blender" : (2, 79, 0),              
    "location" : "View3D > Toolshelf > Normal",   
    "description" : "Edit Custom Normal(s)",   
    "warning" : "",
    "wiki_url" : "https://github.com/dskjal/Smooth-Normal",                    
    "tracker_url" : "",                 
    "category" : "Mesh"                   
}
#----------------------------------------------------------helper tools-----------------------------------------------------
def get_vertex_normal(data, index):
    normal = data.vertices[index].normal
    if data.has_custom_normals:
        for l in data.loops:
            if index == l.vertex_index:
                return l.normal
    
    return normal

def get_vertex_normals(data):
    normals = [(0.0,0.0,0.0)]*len(data.vertices)
    if data.has_custom_normals:
        data.calc_normals_split()
        for poly in data.polygons:
          for i in range( poly.loop_start, poly.loop_start + poly.loop_total ):
              l = data.loops[i]
              normals[l.vertex_index] = l.normal         
    else:
        for i in data.vertices:
            normals[i.index] = i.normal
            
    return normals

def get_loop_normals(data):
    data.calc_normals_split()
    return [l.normal for l in data.loops]
    
def create_loop_table(data):
    to_loops = [[] for row in range(len(data.vertices))]
        
    for p in data.polygons:
        for i in range( p.loop_start, p.loop_start + p.loop_total ):
            index = data.loops[i].vertex_index
            to_loops[index].append(i)
            
    return to_loops

def get_masked_vertices(context):
    ob = context.active_object         
    scn = context.scene
    vertex_color = scn.ne_vertex_color

    selected = [False]*len(ob.data.vertices)  
    if not scn.ne_mask_name in ob.vertex_groups:
        return selected

    vg_index = ob.vertex_groups[scn.ne_mask_name].index
    
    for v in ob.data.vertices:
        for vg in v.groups:
            if vg.group == vg_index:
                selected[v.index] = True
                      
    return selected

def ensure_lookup_table(bm):
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
#---------------------------------------------------------------function body----------------------------------------------------------------------
def smooth_selected_normals(data, masked_vertices):
    normals = get_loop_normals(data)
    
    out_normals = copy.deepcopy(normals)  
    
    vnormals = get_vertex_normals(data)
   
    to_loops = create_loop_table(data)  
    
    #create edge table
    edges = [[] for row in range(len(data.vertices))]
    for e in data.edges:
        vs = e.vertices
        edges[vs[0]].append(vs[1])
        edges[vs[1]].append(vs[0])
        
    #smooth normals
    selected = [v for v in data.vertices if v.select and not masked_vertices[v.index] ]
    for v in selected:
        cn = mathutils.Vector(vnormals[v.index])
        for e in edges[v.index]:
            cn += vnormals[e]
        
        cn.normalize()
        for f in to_loops[v.index]:
            out_normals[f] = cn
        
    data.normals_split_custom_set(out_normals)

def restore_selected_normals(data, masked_vertices):
    normals = get_loop_normals(data)
    to_loops = create_loop_table(data)
    
    selected = [v for v in data.vertices if v.select and not masked_vertices[v.index] ]
    for s in selected:
        for f in to_loops[s.index]:
            normals[f] = s.normal
            
    data.normals_split_custom_set(normals)

def set_same_normal(data, normal, masked_vertices):
    normals = get_loop_normals(data)  
    to_loops = create_loop_table(data)
        
    #update normals
    selected = [v for v in data.vertices if v.select and not masked_vertices[v.index] ]
    for v in selected:
        for f in to_loops[v.index]:
            normals[f] = normal
        
    data.normals_split_custom_set(normals)
   
def set_loop_normal(data, normal, loop_index, masked_vertices):
    normals = get_loop_normals(data)  
        
    #update normals
    selected = [l for l in loop_index if not masked_vertices[ data.loops[l].vertex_index ]]
    for s in selected:
        normals[s] = normal

    data.normals_split_custom_set(normals)

def set_face_normal(data, masked_vertices):
    normals = get_loop_normals(data)

    selected = [p for p in data.polygons if p.select]
    for s in selected:
        for i in range( s.loop_start, s.loop_start + s.loop_total ):
            if not masked_vertices[data.loops[i].vertex_index]:
                normals[i] = s.normal      
    
    data.normals_split_custom_set(normals)  

# BMesh become invalid
# if there is no active, return None
# else return [normal, bm.select_history.active.index, loop_index]
def get_active_normal(context,ob):
    scn = context.scene
    bm = bmesh.from_edit_mesh(ob.data)
    ensure_lookup_table(bm)
    active = bm.select_history.active
    if not active:
        return None

    index = active.index
    to_loops = create_loop_table(ob.data)
    loop_normals = get_loop_normals(ob.data)
    loop_index = -1

    normal = active.normal
    if bpy.context.scene.tool_settings.mesh_select_mode[0]:
        #vertex
        if scn.ne_split_mode:
            loop_index = scn.ne_view_normal_index
            if loop_index < len(to_loops[index]):
                loop_index = to_loops[index][loop_index]
                normal = ob.data.loops[loop_index].normal
        else:
            for f in to_loops[index]:
                if ob.data.loops[f].vertex_index==index:
                    normal = ob.data.loops[f].normal
                    loop_index = ob.data.loops[f].index
                    break
        
    return [normal, index, loop_index]

def update_active_normal(context, ob):
    scn = context.scene
    normal = get_active_normal(context, ob)
    if normal==None:
        return

    if scn.ne_split_mode:
        loop_index = normal[2]
        if loop_index!=-1:
            normal = ob.data.loops[loop_index].normal
        else:
            normal = normal[0]
    else:
        normal = normal[0]

    scn.ne_type_normal = normal

def set_normal_to_selected(context, normal):
    scn = context.scene
    o = context.active_object   
    bm = bmesh.from_edit_mesh(o.data)
    ensure_lookup_table(bm)  
    if not hasattr(bm.select_history.active,'index'):
        return
    index = bm.select_history.active.index
    masked_vertices = get_masked_vertices(context)  

    bpy.ops.object.mode_set(mode='OBJECT')

    if scn.ne_split_mode:
        if scn.tool_settings.mesh_select_mode[0]:
            #split vertex mode
            loop_index = scn.ne_view_normal_index
            to_loops = create_loop_table(o.data)
            if loop_index < len(to_loops[index]):
                loop_index = to_loops[index][loop_index]                                
                set_loop_normal(o.data, normal, [loop_index], masked_vertices)
        if scn.tool_settings.mesh_select_mode[2]:
            #split face mode
            selected = [p for p in o.data.polygons if p.select]
            loop_index = []
            for s in selected:
                for i in range( s.loop_start, s.loop_start + s.loop_total ):
                    loop_index.append(i)  
            set_loop_normal(o.data, normal, loop_index, masked_vertices)
    else:
        set_same_normal(o.data, normal, masked_vertices)

    bpy.context.scene.update()
    bpy.ops.object.mode_set(mode='EDIT')        
  
#----------------------------------------------------show normal tools----------------------------------------------------------
def is_same_vector(v1,v2):
    for e1,e2 in zip(v1,v2):
        if e1!=e2:
            return False

    return True

def get_view_quaternion():
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            return area.spaces[0].region_3d.view_rotation

def get_view_rotational_matrix(reverse=False):
    qt = mathutils.Quaternion(bpy.context.scene.ne_view_orientation)
    if reverse:
        qt.conjugate()

    return qt.to_matrix()

def get_object_rotational_matrix():
    return mathutils.Matrix(bpy.context.active_object.matrix_world).to_quaternion().to_matrix()

def rot_vector(v, axis='X', reverse=False, angle=90):
    angle = math.radians(-angle if reverse else angle)
    mRot = mathutils.Matrix.Rotation(angle, 3, 'X')
    return mRot * v

def view_normal_callback(self, context):
    scn = context.scene

    #update from view
    if scn.ne_update_by_global_callback:
        scn.ne_update_by_global_callback = False
        return

    real_normal = scn.ne_view_normal
    if scn.ne_view_sync_mode:
        mView = get_view_rotational_matrix()
        mObject = get_object_rotational_matrix()
        mObject.transpose()
        real_normal = mObject * mView * real_normal
    else:
        real_normal = rot_vector(real_normal)
    
    scn.ne_type_normal = real_normal

def type_direction_callback(self, context):
    scn = context.scene
    v = mathutils.Vector(scn.ne_type_normal)
    
    nv = copy.deepcopy(v)
    nv.normalize()
    rotated = nv

    if scn.ne_view_sync_mode:
        mView = get_view_rotational_matrix(True)
        mObject = get_object_rotational_matrix()
        rotated = mView * mObject * nv
    else:
        rotated = rot_vector(nv, reverse=True)

    if not is_same_vector(scn.ne_type_normal, scn.ne_type_normal_old):
        if not scn.ne_update_by_global_callback:
            set_normal_to_selected(context, nv)
        scn.ne_type_normal_old = scn.ne_type_normal

    # update direction sphere
    # avoid recursive call
    scn.ne_update_by_global_callback = True
    scn.ne_view_normal = rotated
     
def index_callback(self, context):
    scn = context.scene
    if scn.ne_split_mode:
        o = context.active_object   
        bm = bmesh.from_edit_mesh(o.data)
        ensure_lookup_table(bm)  
        index = bm.select_history.active.index
        masked_vertices = get_masked_vertices(context)  

        loop_index = scn.ne_view_normal_index
        to_loops = create_loop_table(o.data)
        if loop_index < len(to_loops[index]):
            o.data.calc_normals_split()
            loop_index = to_loops[index][face_index]
            rotated = o.data.loops[loop_index].normal
            if scn.ne_view_sync_mode:
                mView = get_view_rotational_matrix(True)
                mObject = get_object_rotational_matrix()
                rotated = mView * mObject * rotated
            else:
                rotated = rot_vector(rotated, reverse=True)
            scn.ne_view_normal = rotated

def view_orientation_callback(self, context):
    scn = context.scene
    scn.ne_type_normal = scn.ne_type_normal

def view_sync_toggle_callback(self, context):
    scn = context.scene
    scn.ne_type_normal = scn.ne_type_normal

#------------------------------------------------------------------UI-------------------------------------------------------------------------
class UI(bpy.types.Panel):
  bl_label = "Normal Edit"
  bl_space_type = "VIEW_3D"
  bl_region_type = "TOOLS"
  bl_category = "Normal"
  
  @classmethod
  def poll(self,context):
    ob = context.active_object
    scn = context.scene
    if context.object and context.object.type == 'MESH' and context.object.mode == 'EDIT':
        return 1
                 
  def draw(self, context):
    layout = self.layout
    ob = context.object
    scn = context.scene

    #display
    layout.label(text="Display:")
    layout.prop(ob.data, "use_auto_smooth", text="Activate", toggle=True)
    row = layout.row(align=True)
    row.prop(ob.data,"show_normal_loop",text="",icon="LOOPSEL")
    row.prop(scn.tool_settings, "normal_size", text="Size")
    layout.separator()
    
    #mask tools
    layout.label(text="Mask Tool:")
    layout.prop(ob.data,"show_weight", text="Show Mask",toggle=True)
    layout.operator("smoothnormal.createmask")
    layout.operator("smoothnormal.clearmask")

    #show normal
    layout.separator()
    layout.label(text="Edit Normal:")
    row = layout.row()
    row.prop(scn,"ne_split_mode",toggle=True) 
    row.prop(scn,"ne_view_normal_index")
    layout.prop(scn, "ne_view_sync_mode", toggle=True)
    row = layout.row()
    row.column().prop(scn,"ne_type_normal")
    row.prop(scn,"ne_view_normal")
    layout.separator()
    row = layout.row(align=True)
    row.alignment = "EXPAND"
    row.operator("smoothnormal.copy",icon="COPYDOWN")
    row.operator("smoothnormal.paste",icon="PASTEDOWN")
        
    #basic tools
    layout.separator()
    row = layout.row(align=True)
    row.operator("smoothnormal.smoothnormals")
    row.operator("smoothnormal.revert")
    if context.scene.tool_settings.mesh_select_mode[2]:
        layout.operator("smoothnormal.setfacenormal")

    #layout.operator("smoothnormal.rotate")

#------------------------------------------------------------------Operator(Button)----------------------------------------------------
class SmoothButton(bpy.types.Operator):
  bl_idname = "smoothnormal.smoothnormals"
  bl_label = "Smooth"
  
  def execute(self, context):
    o = bpy.context.active_object
    masked_vertices = get_masked_vertices(context)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    smooth_selected_normals(o.data, masked_vertices)
    bpy.context.scene.update()
    bpy.ops.object.mode_set(mode='EDIT')
    update_active_normal(context,o)
    bpy.ops.object.mode_set(mode='EDIT')

    return{'FINISHED'}
    
class RevertButton(bpy.types.Operator):
    bl_idname = "smoothnormal.revert"
    bl_label = "Restore"
    
    def execute(self, context):
        o = bpy.context.active_object
        masked_vertices = get_masked_vertices(context)
        
        bpy.ops.object.mode_set(mode='OBJECT')       
        restore_selected_normals(o.data, masked_vertices)
        bpy.context.scene.update()
        bpy.ops.object.mode_set(mode='EDIT')
        update_active_normal(context, o)
        bpy.ops.object.mode_set(mode='EDIT')

        return{'FINISHED'}
    
class SetFaceNormal(bpy.types.Operator):
    bl_idname = "smoothnormal.setfacenormal"
    bl_label = "set face normal"
    
    def execute(self, context):
        o = bpy.context.active_object
        masked_vertices = get_masked_vertices(context)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        set_face_normal(o.data, masked_vertices)
        bpy.context.scene.update()
        bpy.ops.object.mode_set(mode='EDIT')
        #update_active_normal(context, o)
        bpy.ops.object.mode_set(mode='EDIT')
        
        return {'FINISHED'}
    
class CreateMaskButton(bpy.types.Operator):
    bl_idname = "smoothnormal.createmask"
    bl_label = "mask vertex"
    
    def execute(self, context):
        o = context.active_object         
        scn = context.scene

        bpy.ops.object.mode_set(mode='OBJECT')
        
        #create vertex group if not have
        if not scn.ne_mask_name in o.vertex_groups:
            o.vertex_groups.new(scn.ne_mask_name)
        vg = o.vertex_groups[scn.ne_mask_name]
        
        #update vertex group
        selected = [v.index for v in o.data.vertices if v.select]
        vg.add(selected, 1.0, 'REPLACE')

        bpy.ops.object.mode_set(mode='EDIT')
        
        return {'FINISHED'}

class ClearMaskButton(bpy.types.Operator):
    bl_idname = "smoothnormal.clearmask"
    bl_label = "clear selected mask"
    
    def execute(self, context):
        o = context.active_object         
        scn = context.scene

        bpy.ops.object.mode_set(mode='OBJECT')
        
        if not scn.ne_mask_name in o.vertex_groups:
            bpy.ops.object.mode_set(mode='EDIT')
            return {'FINISHED'}
        
        vg = o.vertex_groups[scn.ne_mask_name]
        
        #update vertex group
        selected = [v.index for v in o.data.vertices if v.select]
        vg.remove(selected)

        bpy.ops.object.mode_set(mode='EDIT')
        
        return {'FINISHED'}
    
class CopyButton(bpy.types.Operator):
    bl_idname = "smoothnormal.copy"
    bl_label = "Copy"
    
    def execute(self, context):
        scn = context.scene
        o = bpy.context.active_object           

        normal = get_active_normal(context, o)
        if normal!=None:
            scn.ne_view_normal_cache = normal[0]
            
        return {'FINISHED'}
    
class PasteButton(bpy.types.Operator):
    bl_idname = "smoothnormal.paste"
    bl_label = "Paste"
    
    def execute(self, context):
        set_normal_to_selected(context, context.scene.ne_view_normal_cache)
        bpy.context.scene.update()
        bpy.ops.object.mode_set(mode='EDIT')
        update_active_normal(context,context.active_object)
        bpy.ops.object.mode_set(mode='EDIT')
                    
        return {'FINISHED'}
    
def is_normal_active(ob):
    if not hasattr(ob,'mode'):
        return False
    return ob.mode == 'EDIT' and ob.data.use_auto_smooth and ob.data.show_normal_loop

def global_callback_handler(context):
    ob = bpy.context.active_object
    scn = bpy.context.scene
    if is_normal_active(ob):
        new_orientation = get_view_quaternion()
        if new_orientation==None:
            return

        if not is_same_vector(new_orientation, scn.ne_view_orientation):
            #update view orientation
            scn.ne_update_by_global_callback = True
            scn.ne_view_orientation = new_orientation

        #active vertex changed
        bm = bmesh.from_edit_mesh(ob.data)
        ensure_lookup_table(bm)  
        active = bm.select_history.active
        if active!=None:
            index = active.index
            if index != scn.ne_last_selected_vert_index:
                scn.ne_last_selected_vert_index = index
                scn.ne_update_by_global_callback = True
                scn.ne_type_normal = get_active_normal(bpy.context, ob)[0]

classes = (
    UI,
    SmoothButton,
    RevertButton,
    SetFaceNormal,
    CreateMaskButton,
    ClearMaskButton,
    CopyButton,
    PasteButton
)
def register():
    #for cache
    bpy.types.Scene.ne_view_normal_cache = bpy.props.FloatVectorProperty(name="",subtype='XYZ',min=-1,max=1)
    bpy.types.Scene.ne_last_selected_vert_index = bpy.props.IntProperty(default=-1)
    bpy.types.Scene.ne_view_orientation = bpy.props.FloatVectorProperty(name="",default=(1,1,0,0),size=4,update=view_orientation_callback)

    #for show normals
    bpy.types.Scene.ne_view_sync_mode = bpy.props.BoolProperty(name="View Sync Mode",default=True,update=view_sync_toggle_callback)
    bpy.types.Scene.ne_split_mode = bpy.props.BoolProperty(name="Split Mode",default=False)
    bpy.types.Scene.ne_view_normal_index = bpy.props.IntProperty(name="index",default=0,min=0,update=index_callback)
    bpy.types.Scene.ne_type_normal_old = bpy.props.FloatVectorProperty(name="",default=(1,0,0),subtype='DIRECTION')
    bpy.types.Scene.ne_view_normal = bpy.props.FloatVectorProperty(name="",default=(1,0,0),subtype='DIRECTION',update=view_normal_callback)
    bpy.types.Scene.ne_normal = bpy.props.FloatVectorProperty(name="",default=(1,0,0),subtype='DIRECTION')
    bpy.types.Scene.ne_type_normal = bpy.props.FloatVectorProperty(name="",subtype='XYZ',update=type_direction_callback)
    bpy.types.Scene.ne_update_by_global_callback = bpy.props.BoolProperty(name="Split Mode",default=True)
        
    #for mask color
    bpy.types.Scene.ne_mask_name = bpy.props.StringProperty(default="smooth_normal_mask")
    bpy.types.Scene.ne_vertex_color = bpy.props.FloatVectorProperty(name="",default=(1,0,0),subtype='COLOR_GAMMA')
    bpy.types.Scene.ne_clear_color = bpy.props.FloatVectorProperty(name="",default=(1,1,1),subtype='COLOR_GAMMA')
    
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.handlers.scene_update_post.append(global_callback_handler)

def unregister():
    bpy.app.handlers.scene_update_post.remove(global_callback_handler)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.ne_view_normal_cache
    del bpy.types.Scene.ne_last_selected_vert_index
    del bpy.types.Scene.ne_view_orientation
  
    del bpy.types.Scene.ne_view_sync_mode
    del bpy.types.Scene.ne_split_mode
    del bpy.types.Scene.ne_view_normal_index
    del bpy.types.Scene.ne_type_normal_old
    del bpy.types.Scene.ne_view_normal
    del bpy.types.Scene.ne_normal
    del bpy.types.Scene.ne_type_normal
    del bpy.types.Scene.ne_update_by_global_callback
      
    del bpy.types.Scene.ne_mask_name
    del bpy.types.Scene.ne_vertex_color
    del bpy.types.Scene.ne_clear_color
    
if __name__ == "__main__":
    register()
