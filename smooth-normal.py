import bpy
import math
import mathutils
import copy
import bmesh

bl_info = {
    "name" : "Normal Smooth Tool",             
    "author" : "dskjal",                  
    "version" : (2,0),                  
    "blender" : (2, 7, 7),              
    "location" : "",   
    "description" : "Edit Custom Normal(s)",   
    "warning" : "",
    "wiki_url" : "https://github.com/dskjal/Smooth-Normal",                    
    "tracker_url" : "",                 
    "category" : "Mesh"                   
}

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

def smooth_selected_normals(data):
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
    selected = [v for v in data.vertices if v.select]
    for v in selected:
        cn = mathutils.Vector(vnormals[v.index])
        for e in edges[v.index]:
            cn += vnormals[e]
        
        cn.normalize()
        for f in to_faces[v.index]:
            out_normals[f] = cn
        
    data.normals_split_custom_set(out_normals)
    
def revert_selected_normals(data):
    normals = get_loop_normals(data)
            
    to_faces = create_face_table(data)
            
    for v in data.vertices:
        if v.select:
            for f in to_faces[v.index]:
                normals[f] = v.normal
            
    data.normals_split_custom_set(normals)

def set_same_normal(data, normal):
    normals = get_loop_normals(data)  
    to_faces = create_face_table(data)
        
    #update normals
    selected = [v for v in data.vertices if v.select]
    for v in selected:
        for f in to_faces[v.index]:
            normals[f] = normal
        
    data.normals_split_custom_set(normals)
    
def set_same_average_normal(data):
    normals = get_vertex_normals(data)
        
    #update normals
    normal = mathutils.Vector((0.0,0.0,0.0))
    for v in data.vertices:
        if v.select:
            normal += normals[v.index]
    
    normal.normalize()
        
    set_same_normal(data, normal)
    
def set_face_normal(data):
    normals = get_loop_normals(data)
    for p in data.polygons:
        if p.select:
            normal = p.normal
            for i in range( p.loop_start, p.loop_start + p.loop_total ):
              normals[i] = normal    
    
    data.normals_split_custom_set(normals)  
    
class UI(bpy.types.Panel):
  bl_label = "Normal Edit"
  bl_space_type = "VIEW_3D"
  bl_region_type = "TOOLS"
      
  @classmethod
  def poll(self,context):
    if context.object and context.object.type == 'MESH' and context.object.mode == 'EDIT':
        return 1
      
  def draw(self, context):
    layout = self.layout
    ob = context.object
    row = layout.row()
    layout.operator("smoothnormal.smoothnormals")
    layout.operator("smoothnormal.lastnormal")
    #layout.operator("smoothnormal.sameaveragenormal");
    if context.scene.tool_settings.mesh_select_mode[2]:
        layout.operator("smoothnormal.setfacenormal")
    layout.operator("smoothnormal.revert")
    
class SmoothButton(bpy.types.Operator):
  bl_idname = "smoothnormal.smoothnormals"
  bl_label = "smooth selected normal(s)"
  
  def execute(self, context):
    o = bpy.context.active_object
    o.data.use_auto_smooth = True
    bpy.ops.object.mode_set(mode='OBJECT')
    smooth_selected_normals(o.data)
    bpy.context.scene.update()
    bpy.ops.object.mode_set(mode='EDIT')

    return{'FINISHED'}

class SetSameAverageNormalButton(bpy.types.Operator):
  bl_idname = "smoothnormal.sameaveragenormal"
  bl_label = "set average normal"
  
  def execute(self, context):
    o = bpy.context.active_object
    o.data.use_auto_smooth = True
    bpy.ops.object.mode_set(mode='OBJECT')
    set_same_average_normal(o.data)
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
            if bpy.context.scene.tool_settings.mesh_select_mode[0]:
                bm.verts.ensure_lookup_table()
            elif bpy.context.scene.tool_settings.mesh_select_mode[1]:
                bm.edges.ensure_lookup_table()
            elif bpy.context.scene.tool_settings.mesh_select_mode[2]:
                bm.faces.ensure_lookup_table()
            
            normal = copy.deepcopy(active.normal)
            index = active.index
            
            bpy.ops.object.mode_set(mode='OBJECT')
            if bpy.context.scene.tool_settings.mesh_select_mode[0]:
                normal = get_vertex_normal(o.data, index)
            
            set_same_normal(o.data, normal)
            bpy.context.scene.update()
            bpy.ops.object.mode_set(mode='EDIT')

        return{'FINISHED'}
    
class RevertButton(bpy.types.Operator):
    bl_idname = "smoothnormal.revert"
    bl_label = "revert selected normal(s)"
    
    def execute(self, context):
        o = bpy.context.active_object
        o.data.use_auto_smooth = True
        bpy.ops.object.mode_set(mode='OBJECT')
        revert_selected_normals(o.data)
        bpy.context.scene.update()
        bpy.ops.object.mode_set(mode='EDIT')

        return{'FINISHED'}
    
class SetFaceNormal(bpy.types.Operator):
    bl_idname = "smoothnormal.setfacenormal"
    bl_label = "set face normal"
    
    def execute(self, context):
        o = bpy.context.active_object
        o.data.use_auto_smooth = True
        bpy.ops.object.mode_set(mode='OBJECT')
        set_face_normal(o.data)
        bpy.context.scene.update()
        bpy.ops.object.mode_set(mode='EDIT')
        
        return {'FINISHED'}
    
def register():
    bpy.utils.register_module(__name__)
    
def unregister():
    bpy.utils.unregister_module(__name__)
    
if __name__ == "__main__":
    register()
