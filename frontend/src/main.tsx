import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import Auditoria from './paginas/admin/Auditoria'
import Cargas from './paginas/admin/Cargas'
import ContenidoSitio from './paginas/admin/ContenidoSitio'
import Establecimientos from './paginas/admin/Establecimientos'
import Indicadores from './paginas/admin/Indicadores'
import LayoutAdmin from './paginas/admin/LayoutAdmin'
import MisReportes from './paginas/admin/MisReportes'
import Resumen from './paginas/admin/Resumen'
import Usuarios from './paginas/admin/Usuarios'
import Inicio from './paginas/publico/Inicio'
import Metodologia from './paginas/publico/Metodologia'
import Observatorio from './paginas/publico/Observatorio'
import { ProveedorSesion } from './sesion/sesion'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ProveedorSesion>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Inicio />} />
          <Route path="/observatorio" element={<Observatorio />} />
          <Route path="/metodologia" element={<Metodologia />} />
          <Route path="/admin" element={<LayoutAdmin />}>
            <Route index element={<Resumen />} />
            <Route path="cargas" element={<Cargas />} />
            <Route path="mis-reportes" element={<MisReportes />} />
            <Route path="establecimientos" element={<Establecimientos />} />
            <Route path="indicadores" element={<Indicadores />} />
            <Route path="usuarios" element={<Usuarios />} />
            <Route path="contenido" element={<ContenidoSitio />} />
            <Route path="auditoria" element={<Auditoria />} />
          </Route>
          <Route path="*" element={<Inicio />} />
        </Routes>
      </BrowserRouter>
    </ProveedorSesion>
  </StrictMode>,
)
