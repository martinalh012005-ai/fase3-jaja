-- =====================================================================
-- evidencias_workbench.sql
-- Apoyo para sacar las CAPTURAS REALES de MySQL Workbench del informe.
-- NO forma parte del script integral. Requiere la base ya cargada.
--
-- Cómo usarlo: abrir en Workbench y ejecutar SENTENCIA POR SENTENCIA
-- (poner el cursor dentro de la sentencia y presionar Ctrl+Enter).
-- Cada bloque indica en qué sección del informe va su captura.
-- La captura debe mostrar la sentencia y su resultado (panel Result Grid).
-- =====================================================================
USE turismo_astronomico;

-- ---------------------------------------------------------------------
-- INFORME 6.2 · Verificación de la creación (esperado: 16, 6, 6, 4)
-- ---------------------------------------------------------------------
SELECT
  (SELECT COUNT(*) FROM information_schema.TABLES   WHERE TABLE_SCHEMA='turismo_astronomico' AND TABLE_TYPE='BASE TABLE') AS tablas,
  (SELECT COUNT(*) FROM information_schema.VIEWS    WHERE TABLE_SCHEMA='turismo_astronomico') AS vistas,
  (SELECT COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA='turismo_astronomico') AS rutinas,
  (SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA='turismo_astronomico') AS triggers;

-- ---------------------------------------------------------------------
-- INFORME 6.4 · Conteo de filas de todas las tablas
-- ---------------------------------------------------------------------
SELECT 'region' AS tabla, COUNT(*) AS filas FROM region
UNION ALL SELECT 'centro_astronomico', COUNT(*) FROM centro_astronomico
UNION ALL SELECT 'zona_observacion', COUNT(*) FROM zona_observacion
UNION ALL SELECT 'fenomeno_astronomico', COUNT(*) FROM fenomeno_astronomico
UNION ALL SELECT 'fenomeno_solar', COUNT(*) FROM fenomeno_solar
UNION ALL SELECT 'fenomeno_lunar', COUNT(*) FROM fenomeno_lunar
UNION ALL SELECT 'fenomeno_espacio_profundo', COUNT(*) FROM fenomeno_espacio_profundo
UNION ALL SELECT 'observacion', COUNT(*) FROM observacion
UNION ALL SELECT 'persona', COUNT(*) FROM persona
UNION ALL SELECT 'trabajador', COUNT(*) FROM trabajador
UNION ALL SELECT 'visitante', COUNT(*) FROM visitante
UNION ALL SELECT 'actividad_observacion', COUNT(*) FROM actividad_observacion
UNION ALL SELECT 'reserva', COUNT(*) FROM reserva
UNION ALL SELECT 'evaluacion', COUNT(*) FROM evaluacion
UNION ALL SELECT 'rol', COUNT(*) FROM rol
UNION ALL SELECT 'cuenta_usuario', COUNT(*) FROM cuenta_usuario;

-- ---------------------------------------------------------------------
-- INFORME 6.6 · Integridad (esperado: todo 0)
-- ---------------------------------------------------------------------
SELECT
 (SELECT COUNT(*) FROM reserva r LEFT JOIN visitante v ON v.id_persona = r.id_visitante
   WHERE v.id_persona IS NULL)                                        AS reservas_sin_visitante,
 (SELECT COUNT(*) FROM evaluacion e JOIN reserva r ON r.id_reserva = e.id_reserva
   WHERE r.asistencia_efectiva = 0)                                   AS evaluaciones_sin_asistencia,
 (SELECT COUNT(*) FROM actividad_observacion a JOIN zona_observacion z ON z.id_zona = a.id_zona
   WHERE a.capacidad > z.capacidad_max)                               AS actividades_sobre_capacidad_zona,
 (SELECT COUNT(*) FROM reserva r JOIN actividad_observacion a ON a.id_actividad = r.id_actividad
   WHERE r.asistencia_efectiva = 1 AND a.estado <> 'REALIZADA')       AS asistencias_en_actividad_no_realizada;

-- ---------------------------------------------------------------------
-- INFORME 6.7 · Casos inválidos. CADA UNO DEBE FALLAR (capturar el error).
-- Ejecutar de a una sentencia; Workbench mostrará el error en "Output".
-- ---------------------------------------------------------------------
-- (1) rango de fechas invertido
CALL sp_r1_zonas_mas_visitadas('2026-12-01', '2026-01-01');

-- (2) centro inexistente
CALL sp_r10_zonas_oscuras_y_actividades(999);

-- (3) capacidad de actividad mayor que la de su zona (trigger)
INSERT INTO actividad_observacion (cod_actividad, id_zona, id_guia, nombre, fecha, horario, duracion_min, modalidad, valor, capacidad, estado)
VALUES ('ACT-TEST', 1, NULL, 'Prueba', '2026-12-01', '21:00', 60, 'NOCTURNA', 1000, 9999, 'PROGRAMADA');

-- (4) reserva duplicada (UNIQUE)
INSERT INTO reserva (id_visitante, id_actividad)
SELECT id_visitante, id_actividad FROM reserva LIMIT 1;

-- (5) evaluar sin haber asistido (trigger)
INSERT INTO evaluacion (id_reserva, fecha, calificacion)
SELECT id_reserva, '2026-11-01', 5 FROM reserva WHERE asistencia_efectiva = 0 AND estado = 'CONFIRMADA' LIMIT 1;

-- (6) calificación fuera de rango (CHECK)
INSERT INTO evaluacion (id_reserva, fecha, calificacion)
SELECT id_reserva, '2026-11-01', 9 FROM reserva
WHERE asistencia_efectiva = 1 AND id_reserva NOT IN (SELECT id_reserva FROM evaluacion) LIMIT 1;

-- (7) visitante inexistente (FK)
INSERT INTO reserva (id_visitante, id_actividad) VALUES (99999, 1);

-- (8) fenómeno lunar insertado como solar (FK compuesta)
INSERT INTO fenomeno_solar (id_fenomeno, tipo_evento, duracion_estimada_min, nivel_intensidad)
SELECT id_fenomeno, 'x', 10, 1 FROM fenomeno_astronomico WHERE tipo_clasificacion = 'LUNAR' LIMIT 1;

-- (9) reserva cancelada con asistencia (CHECK)
UPDATE reserva SET estado = 'CANCELADA', asistencia_efectiva = 1 WHERE id_reserva = 1;

-- (10) reserva en actividad sin cupos. Se hace dentro de una transacción que se revierte.
--      Ejecutar las 5 sentencias en orden; la CUARTA debe fallar; luego la quinta (ROLLBACK).
START TRANSACTION;
SET @a := (SELECT r.id_actividad FROM reserva r JOIN actividad_observacion a ON a.id_actividad = r.id_actividad
           WHERE a.estado = 'PROGRAMADA' AND r.estado = 'CONFIRMADA' ORDER BY r.id_actividad LIMIT 1);
UPDATE actividad_observacion SET capacidad = 1 WHERE id_actividad = @a;
INSERT INTO reserva (id_visitante, id_actividad, estado)
SELECT id_persona, @a, 'CONFIRMADA' FROM visitante
WHERE id_persona NOT IN (SELECT id_visitante FROM reserva WHERE id_actividad = @a) LIMIT 1;
ROLLBACK;

-- ---------------------------------------------------------------------
-- INFORME 7 · Código de cada objeto (opcional: muestra el código guardado en el motor)
-- ---------------------------------------------------------------------
SHOW CREATE VIEW v_r2_distribucion_fenomenos;
SHOW CREATE PROCEDURE sp_r1_zonas_mas_visitadas;

-- ---------------------------------------------------------------------
-- INFORME 7 · EJECUCIÓN de los 12 requerimientos (una captura por cada uno)
-- ---------------------------------------------------------------------
-- R1 (procedimiento)
CALL sp_r1_zonas_mas_visitadas('2026-03-01', '2026-06-30');

-- R2 (vista)
SELECT * FROM v_r2_distribucion_fenomenos ORDER BY centro, zona, registros DESC;

-- R3 (vista)
SELECT * FROM v_r3_asistentes_vs_evaluacion ORDER BY asistentes DESC, evaluacion_promedio DESC;

-- R4 (procedimiento)
CALL sp_r4_centros_actividades_visitantes('2026-03-01', '2026-06-30');

-- R5 (vista)
SELECT * FROM v_r5_tasa_asistencia_zona ORDER BY tasa_asistencia_pct DESC;

-- R6 (vista)
SELECT * FROM v_r6_registros_por_fenomeno ORDER BY registros DESC;

-- R7 (vista)
SELECT * FROM v_r7_diversidad_por_centro ORDER BY fenomenos_distintos_del_centro DESC, centro, proporcion_pct DESC;

-- R8 (vista)
SELECT * FROM v_r8_visitantes_participacion ORDER BY reservas DESC, valor_total_reservado DESC;

-- R9 (procedimiento)
CALL sp_r9_actividades_sobre_promedio_centro(8, '2026-01-01', '2026-11-14');

-- R10 (procedimiento)
CALL sp_r10_zonas_oscuras_y_actividades(8);

-- R11 (procedimiento)
CALL sp_r11_visitantes_destacados('2026-01-01', '2026-11-14');

-- R12 (procedimiento)
CALL sp_r12_centros_sobre_promedio_general('2026-01-01', '2026-11-14');
