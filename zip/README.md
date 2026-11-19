# Proyecto Semestral 2026 · TDFI103 · Fase 2 · Caso 2 (Turismo Astronómico)

## Contenido

```
sql/                 01_schema · 02_datos (generado) · 03_vistas · 04_procedimientos · script_integral.sql (entregable)
                     evidencias_workbench.sql (apoyo para las capturas; NO es parte del script integral)
generador/           generar_datos.py  (Python + Faker, semilla fija)
mere/                MERE_Caso2_corregido.drawio (editable) + .png completo + 4 imágenes por sector + generar_mere.py
pmv/                 Streamlit: app.py, db.py, auth.py, paginas/ (reserva, crud_centros, crud_fenomenos, dashboard, usuarios),
                     requirements.txt, Dockerfile
docker/              20_permisos_app.sql (mínimo privilegio para el usuario de la app)
                     verificar_despliegue.py (revisa todo el despliegue Docker con un comando)
docker-compose.yml   MySQL 8 + PMV   ·   .env.example
Informe_Fase2_Caso2_Turismo_Astronomico.docx   Informe final (13 secciones) con espacios para capturas
```

## Cómo reconstruir la base desde cero

Workbench: `File > Open SQL Script > script_integral.sql` y ejecutar todo (rayo).
Consola: `mysql -u root -p < sql/script_integral.sql`

Regenerar los datos: `pip install faker && python generador/generar_datos.py`
(mismo número de semilla = mismo archivo, verificado byte a byte).

## Volúmenes generados (enunciado §6)

| Tabla | Filas | Rango pedido |
|---|---|---|
| region | 8 | 5–10 |
| centro_astronomico | 16 | 12–20 |
| zona_observacion | 48 | 35–60 |
| fenomeno_astronomico | 75 (22 solares, 20 lunares, 28 espacio profundo, 5 no clasificados) | 60–120 |
| observacion (registro zona-fenómeno) | 420 | 250–500 |
| persona = trabajadores + visitantes | 60 + 220 | 40–80 / 150–300 |
| actividad_observacion | 180 | 120–250 |
| reserva | 1294 | 800–1500 |
| evaluacion | 608 | 400–900 |
| cuenta_usuario (3 roles) | 50 | 40–80 |

## Cuentas de prueba (todas con contraseña `Astro2026!`)

`admin` (ADMINISTRADOR) · `operador` (OPERADOR) · `analista` (ANALISTA).
Las contraseñas se guardan como hash PBKDF2-SHA256 (`pbkdf2_sha256$iteraciones$sal$hash`).

## Definiciones de negocio usadas en las consultas

- **Asistente**: reserva `CONFIRMADA` con `asistencia_efectiva = 1`.
- **Actividad realizada**: `estado = 'REALIZADA'`.
- **Tasa de asistencia (R5)**: asistencias efectivas / reservas confirmadas, en actividades realizadas.
- **Subtipo de fenómeno (R2, R7)**: `tipo_evento` (solar y lunar) o `tipo_objeto` (espacio profundo).
- **Oscuridad**: escala 1 (más luz) a 10 (cielo más oscuro).

## Correcciones al MERE de la Fase 1 (para las secciones 3 y 4 del informe)

| # | Corrección | Justificación |
|---|---|---|
| 1 | ZONA–ACTIVIDAD: una zona alberga muchas actividades; cada actividad ocurre en una sola zona (el `.drawio` tenía las cardinalidades invertidas) | Coherencia con la regla de negocio y con R1, R4, R10 |
| 2 | ACTIVIDAD–EVALUACION pasa de (1,N) a (0,N) | Hay actividades sin evaluaciones (programadas, canceladas o sin evaluar) |
| 3 | EVALUACION cuelga de RESERVA (una por reserva) y solo si hubo asistencia | Identifica quién evalúa sin ambigüedad; coherente con R3 y R11 (trigger `trg_evaluacion_asistencia`) |
| 4 | RESERVA, OBSERVACION y CUENTA_USUARIO reciben identificador propio | Eran entidades sin clave; OBSERVACION se repite para la misma zona y fenómeno en distintas fechas |
| 5 | FENOMENO recibe el discriminador `tipo_clasificacion` (parcial y disjunta) | R2 y R7 agrupan por clasificación; "no clasificado" queda cubierto. La FK compuesta impide que un fenómeno esté en dos subtipos |
| 6 | ACTIVIDAD recibe `estado` y `nombre`; RESERVA con CHECK `estado`/`asistencia` | R9 habla de actividades "realizadas"; evita reservas canceladas con asistencia |
| 7 | PERSONA con discriminador (`tipo_persona`), total y disjunta | Misma técnica que FENOMENO |
| 8 | TRABAJADOR se asocia a un CENTRO y la ACTIVIDAD tiene un guía responsable | El personal estaba aislado del dominio |
| 9 | CUENTA–ROL pasa de N:M a N:1 (cada cuenta un rol) | El PMV necesita permisos sin ambigüedad |
| 10 | ZONA: PK sustituta `id_zona` + UNIQUE(id_centro, numero_interno) | Evita FK compuestas hacia ACTIVIDAD y OBSERVACION; conserva la identificación original |
| 11 | `coordenadas` → latitud/longitud; `nombre` → tres columnas; `email` simple y UNIQUE; `fecha_registro` pasa a VISITANTE; `activo` en CENTRO y FENOMENO | Atomicidad (1FN) y desactivación lógica para el CRUD |

Nota técnica: MySQL no permite un CHECK sobre una columna usada en una FK con CASCADE, por eso las FK compuestas de los subtipos usan RESTRICT.

## Reglas de negocio hechas cumplir por el motor

Capacidad de actividad ≤ capacidad de la zona · no reservar en actividades canceladas ni sin cupo ·
una reserva por visitante y actividad · solo evalúa quien asistió · calificación 1–5 ·
reserva cancelada no puede tener asistencia · subtipos coherentes con el discriminador.

## Verificación realizada

El script integral se ejecutó de principio a fin sobre MySQL 8.0.46 sin errores: 16 tablas, 6 vistas,
6 procedimientos, 4 triggers, 41 CHECK, 17 FK. Se probaron 10 casos inválidos (fechas invertidas, centro inexistente,
capacidad excedida, reserva duplicada, evaluar sin asistir, calificación 9, FK inexistente, subtipo incoherente,
cancelada con asistencia, actividad llena) y todos fueron rechazados.

## Despliegue con Docker

```bash
docker compose up --build        # primera vez: crea la BD desde script_integral.sql y levanta la app
# abrir http://localhost:8501     usuario admin / contraseña Astro2026!
docker compose down              # detener (conserva los datos)
docker compose down -v           # detener y BORRAR el volumen (la próxima vez recarga el script)
```
Para comprobar todo de una vez (en otra terminal): `python docker/verificar_despliegue.py` (debe terminar con «TODO OK (10/10)»).
MySQL queda también en `localhost:3307` por si quieren conectar Workbench (usuario `root`, contraseña de `.env.example`).
El script integral se carga solo la primera vez (volumen vacío).

## PMV: las cuatro funcionalidades

| # | Funcionalidad | Dónde | Permiso (rol) |
|---|---|---|---|
| 1 | Formulario transaccional: reserva de un visitante (centro → zona → actividad con cupos → visitante); valida duplicados, cupos y estado; cancelación | `paginas/reserva.py` | `reservas` (ADMINISTRADOR, OPERADOR) |
| 2 | CRUD de **Centro Astronómico** y **Fenómeno Astronómico** (con subtipos); desactivación lógica y eliminación física solo sin dependencias | `crud_centros.py`, `crud_fenomenos.py` | `crud_centros`, `crud_fenomenos` (ADMINISTRADOR) |
| 3 | Login (PBKDF2), 3 roles con permisos distintos, bloqueo real en servidor, gestión de cuentas | `auth.py`, `usuarios.py` | `usuarios` (ADMINISTRADOR) |
| 4 | Dashboard: P1 zonas con más visitantes · P2 composición solar/lunar/espacio profundo · P3 dispersión asistentes vs. evaluación · **P4 propuesta: ingresos y ocupación por modalidad y mes** | `dashboard.py` | `dashboard` (los tres roles) |

Las consultas del PMV son propias; no reutilizan las vistas ni los procedimientos (el enunciado lo exige).
**Pregunta 4 (justificación):** mira rentabilidad y uso de la oferta, distinto de las otras tres. Apoya decidir qué modalidades ampliar,
cuáles reprogramar o ajustar de precio y en qué meses reforzar guías. Ingreso = valor × asistentes efectivos; ocupación = asistentes / capacidad.

Nota sobre los datos: el generador introduce un escenario diseñado en el que la saturación reduce levemente la evaluación
(correlación ≈ −0,5 en P3). Es un supuesto declarado de los datos sintéticos, no un hallazgo real.

## Pruebas realizadas (en mi entorno: MySQL 8.0.46, Python 3.12, Streamlit 1.67)

- Script integral desde cero sin errores; las 12 consultas devuelven filas; 10 casos inválidos rechazados por el motor.
- PMV con pruebas automáticas (framework de pruebas de Streamlit) conectado con el usuario de la app **sin permisos de DDL**:
  login correcto/incorrecto/cuenta desactivada, menú por rol (admin 5 páginas, operador 2, analista 1), acceso forzado a páginas
  prohibidas bloqueado, reserva válida y duplicada, CRUD completo de ambas tablas (crear, modificar, desactivar, eliminar con y sin
  dependencias, validaciones), 5 gráficos Plotly del dashboard, gestión de cuentas.
- Servidor Streamlit real levantado: endpoint de salud `ok`, página principal HTTP 200.
- La secuencia de inicialización del contenedor MySQL se simuló a mano (crear usuario → script integral → permisos mínimos) y funciona.
- `docker-compose.yml` validado como YAML. `requirements.txt` instalado en un entorno limpio con las versiones exactas y la batería de pruebas repetida allí.
- `docker/verificar_despliegue.py` probado contra un Docker simulado (caso correcto y caso con fallas).

**No verificado:** no pude ejecutar Docker ni abrir un navegador en mi entorno. Falta que ustedes corran `docker compose up --build`
una vez y revisen visualmente las pantallas. Si algo falla al construir, envíenme el mensaje de error.

## Presentación de la defensa

Deck de 7 diapositivas (10 min) publicado como artefacto; descargarlo como PowerPoint o PDF para subirlo a Canvas.
Los expositores (A–D) son una propuesta: reemplazarlos por los nombres reales.

## Pendiente (lo que debe hacer el equipo)

1. Capturas **reales** de Workbench por cada vista y procedimiento, y de las pantallas del PMV y de los contenedores.
2. Modelo relacional: *Database > Reverse Engineer* en Workbench sobre la BD cargada; exportar imagen.
3. Matriz de responsabilidades (4 funcionalidades PMV con 4 responsables distintos), bitácoras individuales y conclusiones por integrante.
4. Informe final (13 secciones) y la diapositiva de defensa. Cada integrante debe poder explicar cualquier sentencia y fragmento de código.
