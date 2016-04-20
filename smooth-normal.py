import bpy
import mathutils
import copy

bl_info = {
    "name" : "Normal Smooth Tool",             
    "author" : "dskjal",                  
    "version" : (1,0),                  
    "blender" : (2, 7, 7),              
    "location" : "UV Mapping > Hoge",   
    "description" : "Smooth Custom Normal(s)",   
    "warning" : "",
    "wiki_url" : "https://github.com/dskjal/Normal-Smooth-Tool",                    
    "tracker_url" : "",                 
    "category" : "Mesh"                   
}

def smooth_selected_normals(data):
    #get normals
    normals = [mathutils.Vector((0.0,0.0,0.0))]*len(data.vertices)
    if data.has_custom_normals:
        data.calc_normals_split()
        for poly in data.polygons:
          for i in range( poly.loop_start, poly.loop_start + poly.loop_total ):
              l = data.loops[i]
              normals[l.vertex_index] = l.normal         
    else:
        for i in data.vertices:
            normals[i.index] = i.normal

    out_normals = copy.deepcopy(normals)  
    
    #create edge table
    edges = []
    for i in range(0,len(data.vertices)):
        edges.append([])
    for e in data.edges:
        vs = e.vertices
        edges[vs[0]].append(vs[1])
        edges[vs[1]].append(vs[0])

    #update normals
    selected = [v for v in data.vertices if v.select]
    for v in selected:
        cn = mathutils.Vector(normals[v.index])
        for e in edges[v.index]:
            cn += normals[e]
        cn.normalize()
        out_normals[v.index] = cn
        
    #set normals
    data.normals_split_custom_set_from_vertices(out_normals)
    data.calc_normals_split()
         
    
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
    layout.operator("my.smoothnormals")
    
class SmoothButton(bpy.types.Operator):
  bl_idname = "my.smoothnormals"
  bl_label = "smooth selected normal(s)"
  
  def execute(self, context):
    o = bpy.context.active_object
    o.data.use_auto_smooth = True
    bpy.ops.object.mode_set(mode='OBJECT')
    smooth_selected_normals(o.data)
    bpy.context.scene.update()
    bpy.ops.object.mode_set(mode='EDIT')

    return{'FINISHED'}

def register():
    bpy.utils.register_module(__name__)
    
def unregister():
    bpy.utils.unregister_module(__name__)
    
if __name__ == "__main__":
    register()
