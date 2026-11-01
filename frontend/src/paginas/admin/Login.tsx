import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Marca } from '../../componentes/Marca'
import { useSesion } from '../../sesion/sesion'

export default function Login() {
  const { entrar } = useSesion()
  const [correo, setCorreo] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setEnviando(true); setError(null)
    try { await entrar(correo, contrasena) } catch (err) { setError((err as Error).message) } finally { setEnviando(false) }
  }

  return (
    <div className="grid min-h-screen bg-fondo lg:grid-cols-[1fr_1.1fr]">
      <div className="hidden flex-col items-center justify-center gap-6 border-r border-linea bg-suave p-12 lg:flex">
        <img src="/logo-web.webp" alt="TurisData Azuay - Cuenca" className="w-full max-w-[380px]" width={720} height={706} />
      </div>
      <main className="flex items-center justify-center px-4 py-12">
        <form onSubmit={enviar} className="w-full max-w-sm space-y-5">
          <Marca />
          <div>
            <h1 className="text-3xl">Panel de administración</h1>
            <p className="mt-1 text-sm text-piedra">Ingrese con la cuenta que le asignó la Cámara.</p>
          </div>
          <label className="grid gap-1" htmlFor="correo">
            <span className="text-sm font-semibold">Correo</span>
            <input id="correo" type="email" className="campo" autoComplete="username" required value={correo} onChange={e => setCorreo(e.target.value)} />
          </label>
          <label className="grid gap-1" htmlFor="contrasena">
            <span className="text-sm font-semibold">Contraseña</span>
            <input id="contrasena" type="password" className="campo" autoComplete="current-password" required value={contrasena} onChange={e => setContrasena(e.target.value)} />
          </label>
          {error && <p className="text-sm text-critico" role="alert">{error}</p>}
          <button className="boton w-full justify-center" disabled={enviando}>{enviando ? 'Ingresando…' : 'Ingresar'}</button>
          <Link to="/" className="block text-center text-sm text-piedra hover:text-rojo">Volver al sitio público</Link>
        </form>
      </main>
    </div>
  )
}
