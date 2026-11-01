// Tipos de los datos que devuelve la API.

export type Rol = 'administrador' | 'analista' | 'consulta' | 'asociado'

export const NOMBRE_ROL: Record<Rol, string> = {
  administrador: 'Administrador',
  analista: 'Analista',
  consulta: 'Consulta',
  asociado: 'Establecimiento asociado',
}

export interface Usuario {
  id: number; correo: string; nombre: string; rol: Rol
  establecimiento_id: number | null; codigo_camara: string | null; nombre_comercial: string | null
}

export interface Kpi {
  codigo: string; nombre: string; unidad: string
  valor: number | null; valor_anio_anterior: number | null; variacion_interanual: number | null
  bandera: string | null; n_unidades: number | null; cobertura_pct: number | null
}

export interface Resumen { periodo: string | null; kpis: Kpi[]; ultima_actualizacion: string | null }

export interface Contenido {
  hero_titulo: string; hero_subtitulo: string; camara_nombre: string; camara_descripcion: string
  mision: string; vision: string; servicios: { titulo: string; texto: string }[]
  destino_titulo: string; destino_texto: string
  contacto_direccion: string; contacto_telefono: string; contacto_correo: string; contacto_web: string
  aviso_datos: string
}
