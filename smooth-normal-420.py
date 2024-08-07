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

# bl_info = {
#     "name" : "Normal Smooth Tool",             
#     "author" : "dskjal",                  
#     "version" : (5, 0),                  
#     "blender" : (2, 83, 5),
#     "location" : "View3D > Side Bar > Normal",   
#     "description" : "Edit Custom Normal(s)",   
#     "warning" : "",
#     "wiki_url" : "https://github.com/dskjal/Smooth-Normal",                    
#     "tracker_url" : "",                 
#     "category" : "Mesh"                   
# }
#----------------------------------------------------------helper tools-----------------------------------------------------
def update_scene():
    bpy.context.evaluated_depsgraph_get().update()

# require Object mode
def get_vertex_normal(data, index):
    normal = data.vertices[index].normal
    if data.has_custom_normals:
        for l in data.loops:
            if index == l.vertex_index:
                return l.normal
    
    return normal

# require Object mode
def calc_normals_split(data):
    data.corner_normals

# require Object mode
def get_vertex_normals(data):
    normals = [(0.0,0.0,0.0)]*len(data.vertices)
    if data.has_custom_normals:
        calc_normals_split(data)
        for poly in data.polygons:
            for i in range( poly.loop_start, poly.loop_start + poly.loop_total ):
                l = data.loops[i]
                normals[l.vertex_index] = l.normal         
    else:
        for i in data.vertices:
            normals[i.index] = i.normal
            
    return normals

# require Object mode
def get_loop_normals(data):
    calc_normals_split(data)
    return [l.normal for l in data.loops]
    
# require Object mode
def create_loop_table(data):
    to_loops = [[] for row in range(len(data.vertices))]
        
    for p in data.polygons:
        for i in range( p.loop_start, p.loop_start + p.loop_total ):
            index = data.loops[i].vertex_index
            to_loops[index].append(i)
            
    return to_loops

# return None if can not get
# else return (index, normal)
# require Edit mode
def get_active_vertex_ed(o):
    if o.mode != 'EDIT' or o.type != 'MESH':
        return None

    for v in o.data.vertices:
        if v.select:
            return (v.index, v.normal)

    return None
    
    # vertex weight can not drag when bmesh is accessed while dragging
    # bm = bmesh.from_edit_mesh(o.data)
    # bm.verts.ensure_lookup_table()
    # bm.edges.ensure_lookup_table()
    # bm.faces.ensure_lookup_table()

    # if hasattr(bm.select_history.active, 'index'):
    #     ret = (bm.select_history.active.index, bm.select_history.active.normal)
    # else:
    #     bpy.ops.object.mode_set(mode='OBJECT')
    #     for v in o.data.vertices:
    #         if v.select:
    #             ret = (v.index, v.normal)
    #             break
    #     bpy.ops.object.mode_set(mode='EDIT')
    # return ret

def is_split_mode():
    return bpy.context.scene.dskjal_sn_props.ne_split_mode

def get_loop_index():
    return bpy.context.scene.dskjal_sn_props.ne_view_normal_index

#---------------------------------------------------------------function body----------------------------------------------------------------------
def smooth_selected_normals(data):
    bpy.ops.object.mode_set(mode='OBJECT')
    normals = get_loop_normals(data)
    out_normals = copy.deepcopy(normals)  
    vnormals = get_vertex_normals(data)
    to_loops = create_loop_table(data)  
    
    #create edge table for get active normal
    edges = [[] for row in range(len(data.vertices))]
    for e in data.edges:
        vs = e.vertices
        edges[vs[0]].append(vs[1])
        edges[vs[1]].append(vs[0])
        
    #smooth normals
    selected = [v for v in data.vertices if v.select]
    for v in selected:
        cn = mathutils.Vector(vnormals[v.index])
        for e in edges[v.index]:
            cn += vnormals[e]
        
        cn.normalize()
        for f in to_loops[v.index]:
            out_normals[f] = cn
        
    data.normals_split_custom_set(out_normals)
    bpy.ops.object.mode_set(mode='EDIT')

def restore_selected_normals(data):
    bpy.ops.object.mode_set(mode='OBJECT')
    normals = get_loop_normals(data)
    to_loops = create_loop_table(data)
    
    selected = [v for v in data.vertices if v.select]
    for s in selected:
        for f in to_loops[s.index]:
            normals[f] = s.normal
            
    data.normals_split_custom_set(normals)
    bpy.ops.object.mode_set(mode='EDIT')

def set_same_normal(data, normal):
    bpy.ops.object.mode_set(mode='OBJECT')
    normals = get_loop_normals(data)  
    to_loops = create_loop_table(data)
        
    #update normals
    selected = [v for v in data.vertices if v.select]
    for v in selected:
        for f in to_loops[v.index]:
            normals[f] = normal
        
    data.normals_split_custom_set(normals)
    bpy.ops.object.mode_set(mode='EDIT')
   
def set_loop_normal(data, normal, loop_index):
    bpy.ops.object.mode_set(mode='OBJECT')
    normals = get_loop_normals(data)  
        
    #update normals
    selected = [l for l in loop_index]
    for s in selected:
        normals[s] = normal

    data.normals_split_custom_set(normals)
    bpy.ops.object.mode_set(mode='EDIT')

def set_face_normal(data):
    bpy.ops.object.mode_set(mode='OBJECT')
    normals = get_loop_normals(data)

    selected = [p for p in data.polygons if p.select]
    for s in selected:
        for i in range( s.loop_start, s.loop_start + s.loop_total ):
            normals[i] = s.normal      
    
    data.normals_split_custom_set(normals)
    bpy.ops.object.mode_set(mode='EDIT')

# BMesh become invalid
# if there is no active, return None
# else return [normal, bm.select_history.active.index, loop_index]
def get_active_normal(context,ob):
    active = get_active_vertex_ed(ob)
    if active == None:
        return None

    index = active[0]
    to_loops = create_loop_table(ob.data)
    loop_normals = get_loop_normals(ob.data)
    loop_index = -1

    normal = active[1]
    if bpy.context.scene.tool_settings.mesh_select_mode[0]:
        #vertex
        if is_split_mode():
            loop_index = get_loop_index()
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
    scn = context.scene.dskjal_sn_props
    normal = get_active_normal(context, ob)
    if normal==None:
        return

    if is_split_mode():
        loop_index = normal[2]
        if loop_index != -1:
            normal = ob.data.loops[loop_index].normal
        else:
            normal = normal[0]
    else:
        normal = normal[0]

    scn.ne_type_normal = normal

def set_normal_to_selected(context, normal):
    o = context.active_object
    if not is_split_mode():
        set_same_normal(o.data, normal)
    else:
        bpy.ops.object.mode_set(mode='EDIT')
        active = get_active_vertex_ed(o)
        if active == None:
            return

        index = active[0]
        if bpy.context.scene.tool_settings.mesh_select_mode[0]:
            # split vertex mode
            loop_index = get_loop_index()
            to_loops = create_loop_table(o.data)
            if loop_index < len(to_loops[index]):
                loop_index = to_loops[index][loop_index]
                set_loop_normal(o.data, normal, [loop_index])
        if bpy.context.scene.tool_settings.mesh_select_mode[2]:
            # split face mode
            selected = [p for p in o.data.polygons if p.select]
            loop_index = []
            for s in selected:
                for i in range( s.loop_start, s.loop_start + s.loop_total ):
                    loop_index.append(i)  
            set_loop_normal(o.data, normal, loop_index)

    bpy.ops.object.mode_set(mode='EDIT')        
  
#----------------------------------------------------show normal tools----------------------------------------------------------
def is_same_vector(v1,v2):
    for e1,e2 in zip(v1,v2):
        if e1!=e2:
            return False

    return True

def window_matrix_handler():
    try:
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                bpy.context.scene.dskjal_sn_props.ne_window_rotation = area.spaces[0].region_3d.view_rotation
                bpy.context.scene.dskjal_sn_props.ne_window_rotation_available = True
    except:
        bpy.context.scene.dskjal_sn_props.ne_window_rotation_available = False

def get_view_rotational_matrix(reverse=False):
    qt = mathutils.Quaternion(bpy.context.scene.dskjal_sn_props.ne_window_rotation)
    if reverse:
        qt.conjugate()

    return qt.to_matrix()

def rot_vector(v, axis='X', reverse=False, angle=90):
    angle = math.radians(-angle if reverse else angle)
    mRot = mathutils.Matrix.Rotation(angle, 3, 'X')
    return mRot @ v

def rot_with_view_matrix(vector, reverse=False):
    v = copy.deepcopy(vector)
    if bpy.context.scene.dskjal_sn_props.ne_view_sync_mode:
        mView = get_view_rotational_matrix(reverse=reverse)
        mObject = mathutils.Matrix(bpy.context.view_layer.objects.active.matrix_world).to_quaternion().to_matrix() # get object rotational matrix
        if reverse:
            v = mView @ mObject @ v
        else:
            mObject.transpose()
            v = mObject @ mView @ v
    else:
        v = rot_vector(v, reverse=reverse)
    
    return v

def view_normal_callback(self, context):
    scn = context.scene.dskjal_sn_props

    #update from view
    if scn.ne_update_by_global_callback:
        scn.ne_update_by_global_callback = False
        return

    scn.ne_type_normal = rot_with_view_matrix(scn.ne_view_normal, reverse=False)

def type_direction_callback(self, context):
    scn = context.scene.dskjal_sn_props
    v = mathutils.Vector(scn.ne_type_normal)
    v.normalize()

    v_view = rot_with_view_matrix(v, reverse=True)

    if not is_same_vector(scn.ne_type_normal, scn.ne_type_normal_old):
        if not scn.ne_update_by_global_callback:
            set_normal_to_selected(context, v)
        scn.ne_type_normal_old = scn.ne_type_normal

    # update direction sphere
    # avoid recursive call
    scn.ne_update_by_global_callback = True
    scn.ne_view_normal = v_view
     
def index_callback(self, context):
    if not is_split_mode():
        return

    o = context.active_object   
    active = get_active_vertex_ed(o) 
    if active == None:
        return
    index = active[0]

    loop_index = get_loop_index()
    to_loops = create_loop_table(o.data)
    if loop_index < len(to_loops[index]):
        calc_normals_split(o.data)
        loop_index = to_loops[index][loop_index]
        context.scene.dskjal_sn_props.ne_view_normal = rot_with_view_matrix(o.data.loops[loop_index].normal, reverse=True)

def view_orientation_callback(self, context):
    scn = context.scene.dskjal_sn_props
    scn.ne_type_normal = scn.ne_type_normal

def view_sync_toggle_callback(self, context):
    scn = context.scene.dskjal_sn_props
    scn.ne_type_normal = scn.ne_type_normal

#------------------------------------------------------------------ UI -------------------------------------------------------------------------
class DSKJAL_PT_UI(bpy.types.Panel):
  bl_label = "Normal Edit"
  bl_space_type = "VIEW_3D"
  bl_region_type = "UI"
  bl_category = "Normal Edit"
  
  @classmethod
  def poll(self,context):
    ob = context.active_object
    return ob and ob.type == 'MESH' and ob.mode == 'EDIT'
                 
  def draw(self, context):
    layout = self.layout
    ob = context.object
    scn = context.scene.dskjal_sn_props
    overlay = bpy.context.space_data.overlay

    #display
    layout.label(text="Display:")
    #layout.prop(ob.data, "use_auto_smooth", text="Activate", toggle=True)
    row = layout.row(align=True)
    row.prop(overlay, "show_split_normals", text="", icon="NORMALS_VERTEX_FACE")
    row.prop(overlay, "normals_length", text="Size")
    layout.separator()

    if ob.mode != 'EDIT':
        return
    if bpy.context.scene.tool_settings.mesh_select_mode[1]:
        # edge select mode
        return

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

#------------------------------------------------------------------ Operator ----------------------------------------------------
class DSKJAL_OT_SmoothButton(bpy.types.Operator):
    bl_idname = "smoothnormal.smoothnormals"
    bl_label = "Smooth"
  
    def execute(self, context):
        o = bpy.context.view_layer.objects.active
    
        smooth_selected_normals(o.data)
        update_active_normal(context,o)
        update_scene()

        return{'FINISHED'}
    
class DSKJAL_OT_RevertButton(bpy.types.Operator):
    bl_idname = "smoothnormal.revert"
    bl_label = "Restore"
    
    def execute(self, context):
        o = bpy.context.view_layer.objects.active
        
        restore_selected_normals(o.data)
        update_active_normal(context, o)
        update_scene()

        return{'FINISHED'}
    
class DSKJAL_OT_SetFaceNormal(bpy.types.Operator):
    bl_idname = "smoothnormal.setfacenormal"
    bl_label = "Set Face Normal"
    
    def execute(self, context):
        o = bpy.context.view_layer.objects.active
        
        set_face_normal(o.data)
        update_active_normal(context, o)
        update_scene()
        
        return {'FINISHED'}
    
class DSKJAL_OT_CopyButton(bpy.types.Operator):
    bl_idname = "smoothnormal.copy"
    bl_label = "Copy"
    
    def execute(self, context):
        scn = context.scene.dskjal_sn_props
        o = bpy.context.view_layer.objects.active           

        normal = get_active_normal(context, o)
        if normal != None:
            scn.ne_view_normal_cache = normal[0]
            
        return {'FINISHED'}
    
class DSKJAL_OT_PasteButton(bpy.types.Operator):
    bl_idname = "smoothnormal.paste"
    bl_label = "Paste"
    
    def execute(self, context):
        set_normal_to_selected(context, context.scene.dskjal_sn_props.ne_view_normal_cache)
        update_active_normal(context,context.active_object)
        update_scene()
                    
        return {'FINISHED'}
    
def is_normal_active(ob):
    if not getattr(ob,'mode', False) or ob.mode != 'EDIT':
        return False
    return bpy.context.scene.dskjal_sn_props.ne_view_sync_mode

def get_window_rotation():
    if bpy.context.scene.dskjal_sn_props.ne_window_rotation_available:
        return bpy.context.scene.dskjal_sn_props.ne_window_rotation
    return None


def global_callback_handler():
    interval = 0.5
    ob = bpy.context.view_layer.objects.active
    scn = bpy.context.scene.dskjal_sn_props
    if is_normal_active(ob):
        new_rotation = get_window_rotation()
        if new_rotation == None:
            return interval

        if not is_same_vector(new_rotation, scn.ne_view_orientation):
            #update view orientation
            scn.ne_update_by_global_callback = True
            scn.ne_view_orientation = new_rotation
            scn.ne_window_rotation = new_rotation

        #active vertex changed
        active = get_active_vertex_ed(ob)
        if active != None:
            index = active[0]
            if index != scn.ne_last_selected_vert_index:
                scn.ne_last_selected_vert_index = index
                scn.ne_update_by_global_callback = True
                scn.ne_type_normal = get_active_normal(bpy.context, ob)[0]

    return interval

#------------------------------------------- Register ----------------------------------------------------------
class DSKJAL_SN_Props(bpy.types.PropertyGroup):
    #for cache
    ne_view_normal_cache : bpy.props.FloatVectorProperty(name="", subtype='XYZ', min=-1, max=1)
    ne_last_selected_vert_index : bpy.props.IntProperty(default=-1)
    ne_view_orientation : bpy.props.FloatVectorProperty(name="",default=(1,1,0,0),size=4,update=view_orientation_callback)
    ne_window_rotation : bpy.props.FloatVectorProperty(name="",default=(1,1,0,0),size=4)
    ne_window_rotation_available : bpy.props.BoolProperty(default=False)

    #for show normals
    ne_view_sync_mode : bpy.props.BoolProperty(name="View Sync Mode",default=True,update=view_sync_toggle_callback)
    ne_split_mode : bpy.props.BoolProperty(name="Split Mode",default=False)
    ne_view_normal_index : bpy.props.IntProperty(name="index",default=0,min=0,update=index_callback)
    ne_type_normal_old : bpy.props.FloatVectorProperty(name="",default=(1,0,0),subtype='DIRECTION')
    ne_view_normal : bpy.props.FloatVectorProperty(name="",default=(1,0,0),subtype='DIRECTION',update=view_normal_callback)
    ne_type_normal : bpy.props.FloatVectorProperty(name="",subtype='XYZ',update=type_direction_callback)
    ne_update_by_global_callback : bpy.props.BoolProperty(name="Split Mode",default=True)
        
class Handler_Class:
    __handle = None

    @staticmethod
    def add_handle():
        Handler_Class.__handle = bpy.types.SpaceView3D.draw_handler_add(window_matrix_handler, (), 'WINDOW', 'POST_PIXEL')

    @staticmethod
    def remove_handle():
        if Handler_Class.__handle != None:
            bpy.types.SpaceView3D.draw_handler_remove(Handler_Class.__handle, 'WINDOW')
            Handler_Class.__handle = None

classes = (
    DSKJAL_PT_UI,
    DSKJAL_OT_SmoothButton,
    DSKJAL_OT_RevertButton,
    DSKJAL_OT_SetFaceNormal,
    DSKJAL_OT_CopyButton,
    DSKJAL_OT_PasteButton,
    DSKJAL_SN_Props
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.dskjal_sn_props = bpy.props.PointerProperty(type=DSKJAL_SN_Props)
    bpy.app.timers.register(global_callback_handler, persistent=True)
    Handler_Class.add_handle()

def unregister():
    Handler_Class.remove_handle()
    bpy.app.timers.unregister(global_callback_handler)
    if getattr(bpy.types.Scene, "dskjal_sn_props", False): del bpy.types.Scene.dskjal_sn_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    
if __name__ == "__main__":
    register()
