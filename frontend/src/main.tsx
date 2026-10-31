import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import Cargas from './admin/Cargas'
import Establecimientos from './admin/Establecimientos'
import LayoutAdmin from './admin/Layout'
import { Auditoria, ContenidoSitio, Indicadores, MisReportes } from './admin/Otras'
import Resumen from './admin/Resumen'
import { ProveedorSesion } from './admin/sesion'
import Usuarios from './admin/Usuarios'
import Inicio from './paginas/Inicio'
import Metodologia from './paginas/Metodologia'
import Observatorio from './paginas/Observatorio'

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
