import bpy
import math
import mathutils
import copy
import bmesh
from bpy.props import *

bl_info = {
    "name" : "Normal Smooth Tool",             
    "author" : "dskjal",                  
    "version" : (3,0),                  
    "blender" : (2, 7, 7),              
    "location" : "",   
    "description" : "Edit Custom Normal(s)",   
    "warning" : "",
    "wiki_url" : "https://github.com/dskjal/Smooth-Normal",                    
    "tracker_url" : "",                 
    "category" : "Mesh"                   
}

#----------------------------------------------------------debug tools------------------------------------------------------
#----------------------------------------------------------helper tools-----------------------------------------------------
def get_vertex_normal(data, index):
    normal = data.vertices[index].normal
    if data.has_custom_normals:
        for l in data.loops:
            if index == l.vertex_index:
                return l.normal
            
    return normal

def get_vertex_normal_bm(bm, index):
    return bm.verts[index].normal

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
    normals = []
    for l in data.loops:
        normals.append(l.normal)
     
    return normals
    
def create_face_table(data):
    to_faces = []
    for i in range(0, len(data.vertices)):
        to_faces.append([])
        
    for p in data.polygons:
        for i in range( p.loop_start, p.loop_start + p.loop_total ):
            index = data.loops[i].vertex_index
            to_faces[index].append(i)
            
    return to_faces

def get_masked_vertices(context):
    ob = context.active_object         
    scn = context.scene
    vertex_color = scn.ne_vertex_color
        
    vg_index = ob.vertex_groups[scn.ne_mask_name].index
    selected = [False]*len(ob.data.vertices)
    for v in ob.data.vertices:
        for vg in v.groups:
            if vg.group == vg_index:
                selected[v.index] = True
                      
    return selected

def ensure_lookup_table(bm):
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
def create_bm_vertex_to_face_table(bm):
    to_faces = []
    for i in range(0, len(bm.verts)):
        to_faces.append([])
        
    for f in bm.faces:
        for v in f.verts:
            to_faces[v.index].append(f.index)
            
    return to_faces   
#---------------------------------------------------------------function body----------------------------------------------------------------------
def smooth_selected_normals(data, masked_vertices):
    normals = get_loop_normals(data)
    
    out_normals = copy.deepcopy(normals)  
    
    vnormals = get_vertex_normals(data)
   
    to_faces = create_face_table(data)  
    
    #create edge table
    edges = []
    for i in range(0,len(data.vertices)):
        edges.append([])
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
        for f in to_faces[v.index]:
            out_normals[f] = cn
        
    data.normals_split_custom_set(out_normals)

def revert_selected_normals(data, masked_vertices):
    normals = get_loop_normals(data)
            
    to_faces = create_face_table(data)
    
    selected = [v for v in data.vertices if v.select and not masked_vertices[v.index] ]
    for s in selected:
        for f in to_faces[s.index]:
            normals[f] = s.normal
            
    data.normals_split_custom_set(normals)

def set_same_normal(data, normal, masked_vertices):
    normals = get_loop_normals(data)  
    to_faces = create_face_table(data)
        
    #update normals
    selected = [v for v in data.vertices if v.select and not masked_vertices[v.index] ]
    for v in selected:
        for f in to_faces[v.index]:
            normals[f] = normal
        
    data.normals_split_custom_set(normals)
    
def set_face_normal(data, masked_vertices):
    normals = get_loop_normals(data)
    for p in data.polygons:
        if p.select:
            normal = p.normal
            for i in range( p.loop_start, p.loop_start + p.loop_total ):
                if not masked_vertices[data.loops[i].vertex_index]:
                    normals[i] = normal    
    
    data.normals_split_custom_set(normals)  

#----------------------------------------------------show normal tools----------------------------------------------------------
def direction_callback(self, context):
    context.scene.ne_type_normal = context.scene.ne_normal

def get_changed_index(context):
    out = []
    scn = context.scene
    for i in range(0,3):
        if scn.ne_old_type_normal[i]!=scn.ne_type_normal[i]:
            out.append(i)
    
    return out

def type_direction_callback(self, context):
    scn = context.scene
    v = mathutils.Vector(scn.ne_type_normal)
    changed_index = get_changed_index(context)
    
    #check 1 or -1
    if len(changed_index)==1:
        i = changed_index[0]
        if v[i]==1 or v[i]==-1:
            new = [0,0,0]
            new[i] = v[i]
            v = new
        else:
            v.normalize()
    else:
        v.normalize()
        
    scn.ne_normal = v
    scn.ne_old_type_normal = scn.ne_normal
     
#------------------------------------------------------------------UI-------------------------------------------------------------------------
class UI(bpy.types.Panel):
  bl_label = "Normal Edit"
  bl_space_type = "VIEW_3D"
  bl_region_type = "TOOLS"
  
  #for cache
  bpy.types.Scene.ne_normal_cache = bpy.props.FloatVectorProperty(name="",subtype='XYZ',min=-1,max=1)
  
  #for show normals
  bpy.types.Scene.ne_split_mode = bpy.props.BoolProperty(name="Split Mode",default=False)
  bpy.types.Scene.ne_normal_index = bpy.props.IntProperty(name="index",default=0,min=0)
  bpy.types.Scene.ne_normal = bpy.props.FloatVectorProperty(name="",default=(1,0,0),subtype='DIRECTION',update=direction_callback)
  bpy.types.Scene.ne_type_normal = bpy.props.FloatVectorProperty(name="",subtype='XYZ',min=-1,max=1,update=type_direction_callback)
  bpy.types.Scene.ne_old_type_normal = bpy.props.FloatVectorProperty(name="old")
      
  #for mask color
  bpy.types.Scene.ne_mask_name = bpy.props.StringProperty(default="smooth_normal_mask")
  bpy.types.Scene.ne_vertex_color = bpy.props.FloatVectorProperty(name="",default=(1,0,0),subtype='COLOR_GAMMA')
  bpy.types.Scene.ne_clear_color = bpy.props.FloatVectorProperty(name="",default=(1,1,1),subtype='COLOR_GAMMA')
  
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
    row = layout.row()
    
    #basic tools
    layout.operator("smoothnormal.smoothnormals")
    layout.operator("smoothnormal.lastnormal")
    if context.scene.tool_settings.mesh_select_mode[2]:
        layout.operator("smoothnormal.setfacenormal")
    layout.operator("smoothnormal.revert")
    layout.separator()
    
    #mask tools
    layout.label(text="Mask Tool")
    layout.prop(ob.data,"show_weight", text="Show Mask")
    layout.operator("smoothnormal.createmask")
    layout.operator("smoothnormal.clearmask")

    #show normal
    '''
    layout.separator()
    layout.label(text="Edit Normal")
    row = layout.row()
    row.prop(scn,"ne_split_mode",toggle=True) 
    row.prop(scn,"ne_normal_index")
    row = layout.row()
    row.column().prop(scn,"ne_type_normal")
    row.prop(scn,"ne_normal")
    layout.separator()
    row = layout.row(align=True)
    row.alignment = "EXPAND"
    row.operator("smoothnormal.copy",icon="COPYDOWN")
    row.operator("smoothnormal.paste",icon="PASTEDOWN")
    '''
    
    
    
#------------------------------------------------------------------Operator(Button)----------------------------------------------------
class SmoothButton(bpy.types.Operator):
  bl_idname = "smoothnormal.smoothnormals"
  bl_label = "smooth selected normal(s)"
  
  def execute(self, context):
    o = bpy.context.active_object
    o.data.use_auto_smooth = True
    masked_vertices = get_masked_vertices(context)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    smooth_selected_normals(o.data, masked_vertices)
    bpy.context.scene.update()
    bpy.ops.object.mode_set(mode='EDIT')

    return{'FINISHED'}
        
class SetSameNormalLastButton(bpy.types.Operator):
    bl_idname = "smoothnormal.lastnormal"
    bl_label = "set last selected normal"
    
    def execute(self, context):
        o = bpy.context.active_object
        o.data.use_auto_smooth = True
            
        bm = bmesh.from_edit_mesh(o.data)
        active = bm.select_history.active
        if active:
            ensure_lookup_table(bm)
            normal = copy.deepcopy(active.normal)
            index = active.index
            masked_vertices = get_masked_vertices(context)
            
            bpy.ops.object.mode_set(mode='OBJECT')
            if bpy.context.scene.tool_settings.mesh_select_mode[0]:
                normal = get_vertex_normal(o.data, index)
            
            set_same_normal(o.data, normal, masked_vertices)
            bpy.context.scene.update()
            bpy.ops.object.mode_set(mode='EDIT')

        return{'FINISHED'}
    
class RevertButton(bpy.types.Operator):
    bl_idname = "smoothnormal.revert"
    bl_label = "revert selected normal(s)"
    
    def execute(self, context):
        o = bpy.context.active_object
        o.data.use_auto_smooth = True
        masked_vertices = get_masked_vertices(context)
        
        bpy.ops.object.mode_set(mode='OBJECT')       
        revert_selected_normals(o.data, masked_vertices)
        bpy.context.scene.update()
        bpy.ops.object.mode_set(mode='EDIT')

        return{'FINISHED'}
    
class SetFaceNormal(bpy.types.Operator):
    bl_idname = "smoothnormal.setfacenormal"
    bl_label = "set face normal"
    
    def execute(self, context):
        o = bpy.context.active_object
        o.data.use_auto_smooth = True
        masked_vertices = get_masked_vertices(context)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        set_face_normal(o.data, masked_vertices)
        bpy.context.scene.update()
        bpy.ops.object.mode_set(mode='EDIT')
        
        return {'FINISHED'}
   
    
class CreateMaskButton(bpy.types.Operator):
    bl_idname = "smoothnormal.createmask"
    bl_label = "mask normal(s)"
    
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
        bm = bmesh.from_edit_mesh(o.data)
        ensure_lookup_table(bm)
        for f in bm.faces:
            for v in f.verts:
                v.normal = (1,0,0)
                
        if scn.ne_split_mode:
            i=0
        else:
            j=0
        return {'FINISHED'}
    
class PasteButton(bpy.types.Operator):
    bl_idname = "smoothnormal.paste"
    bl_label = "Paste"
    
    def execute(self, context):
        return {'FINISHED'}
    

def register():
    bpy.utils.register_module(__name__)
    
def unregister():
    bpy.utils.unregister_module(__name__)
    
if __name__ == "__main__":
    register()
