-- =====================================================================
-- 03_vistas.sql : 6 vistas (R2, R3, R5, R6, R7, R8)
-- Convenciones del modelo:
--   * "Asistente"  = reserva CONFIRMADA con asistencia_efectiva = 1
--   * Solo se consideran actividades REALIZADAS en las vistas de asistencia
-- =====================================================================
USE turismo_astronomico;

-- ---------------------------------------------------------------------
-- R2. Distribución de fenómenos clasificados (solar / lunar / espacio
--     profundo) por centro y zona donde fueron observados.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_r2_distribucion_fenomenos AS
SELECT  c.nombre                         AS centro,
        z.nombre                         AS zona,
        f.tipo_clasificacion             AS clasificacion,
        COUNT(DISTINCT f.id_fenomeno)    AS fenomenos_distintos,
        COUNT(o.id_observacion)          AS registros,
        ROUND(100 * COUNT(o.id_observacion) /
              SUM(COUNT(o.id_observacion)) OVER (PARTITION BY c.id_centro, z.id_zona), 2)
                                         AS pct_en_la_zona
FROM    observacion o
JOIN    fenomeno_astronomico f ON f.id_fenomeno = o.id_fenomeno
JOIN    zona_observacion z     ON z.id_zona     = o.id_zona
JOIN    centro_astronomico c   ON c.id_centro   = z.id_centro
WHERE   f.tipo_clasificacion IN ('SOLAR','LUNAR','ESPACIO_PROFUNDO')
GROUP BY c.id_centro, c.nombre, z.id_zona, z.nombre, f.tipo_clasificacion;

-- ---------------------------------------------------------------------
-- R3. Relación entre asistentes a una actividad y su evaluación promedio.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_r3_asistentes_vs_evaluacion AS
SELECT  a.id_actividad,
        a.cod_actividad,
        a.nombre                                   AS actividad,
        a.modalidad,
        c.nombre                                   AS centro,
        z.nombre                                   AS zona,
        a.capacidad,
        COALESCE(SUM(r.asistencia_efectiva), 0)    AS asistentes,
        COUNT(e.id_evaluacion)                     AS evaluaciones,
        ROUND(AVG(e.calificacion), 2)              AS evaluacion_promedio
FROM    actividad_observacion a
JOIN    zona_observacion z   ON z.id_zona   = a.id_zona
JOIN    centro_astronomico c ON c.id_centro = z.id_centro
LEFT JOIN reserva r          ON r.id_actividad = a.id_actividad AND r.estado = 'CONFIRMADA'
LEFT JOIN evaluacion e       ON e.id_reserva = r.id_reserva
WHERE   a.estado = 'REALIZADA'
GROUP BY a.id_actividad, a.cod_actividad, a.nombre, a.modalidad, c.nombre, z.nombre, a.capacidad;

-- ---------------------------------------------------------------------
-- R5. Tasa de asistencia efectiva por zona respecto del total de reservas
--     (confirmadas) realizadas.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_r5_tasa_asistencia_zona AS
SELECT  c.nombre                                   AS centro,
        z.nombre                                   AS zona,
        COUNT(DISTINCT a.id_actividad)             AS actividades,
        COUNT(r.id_reserva)                        AS reservas_confirmadas,
        SUM(r.asistencia_efectiva)                 AS asistencias_efectivas,
        ROUND(100 * SUM(r.asistencia_efectiva) / COUNT(r.id_reserva), 2) AS tasa_asistencia_pct
FROM    reserva r
JOIN    actividad_observacion a ON a.id_actividad = r.id_actividad
JOIN    zona_observacion z      ON z.id_zona      = a.id_zona
JOIN    centro_astronomico c    ON c.id_centro    = z.id_centro
WHERE   r.estado = 'CONFIRMADA' AND a.estado = 'REALIZADA'
GROUP BY c.id_centro, c.nombre, z.id_zona, z.nombre;

-- ---------------------------------------------------------------------
-- R6. Fenómenos con mayor cantidad de registros de observación por
--     centro y zona.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_r6_registros_por_fenomeno AS
SELECT  f.nombre                 AS fenomeno,
        f.tipo_clasificacion     AS clasificacion,
        c.nombre                 AS centro,
        z.nombre                 AS zona,
        COUNT(o.id_observacion)  AS registros,
        MIN(o.fecha)             AS primera_observacion,
        MAX(o.fecha)             AS ultima_observacion,
        SUM(o.resultado = 'EXITOSA') AS observaciones_exitosas
FROM    observacion o
JOIN    fenomeno_astronomico f ON f.id_fenomeno = o.id_fenomeno
JOIN    zona_observacion z     ON z.id_zona     = o.id_zona
JOIN    centro_astronomico c   ON c.id_centro   = z.id_centro
GROUP BY f.id_fenomeno, f.nombre, f.tipo_clasificacion, c.id_centro, c.nombre, z.id_zona, z.nombre;

-- ---------------------------------------------------------------------
-- R7. Diversidad de fenómenos por centro y proporción de cada tipo
--     (y subtipo) respecto de los fenómenos distintos del centro.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_r7_diversidad_por_centro AS
SELECT  c.nombre                                   AS centro,
        f.tipo_clasificacion                       AS clasificacion,
        COALESCE(s.tipo_evento, l.tipo_evento, ep.tipo_objeto, 'sin subtipo') AS subtipo,
        COUNT(DISTINCT f.id_fenomeno)              AS fenomenos_distintos,
        COUNT(o.id_observacion)                    AS registros,
        t.fenomenos_centro                         AS fenomenos_distintos_del_centro,
        ROUND(100 * COUNT(DISTINCT f.id_fenomeno) / t.fenomenos_centro, 2) AS proporcion_pct
FROM    observacion o
JOIN    fenomeno_astronomico f          ON f.id_fenomeno = o.id_fenomeno
LEFT JOIN fenomeno_solar s              ON s.id_fenomeno = f.id_fenomeno
LEFT JOIN fenomeno_lunar l              ON l.id_fenomeno = f.id_fenomeno
LEFT JOIN fenomeno_espacio_profundo ep  ON ep.id_fenomeno = f.id_fenomeno
JOIN    zona_observacion z              ON z.id_zona     = o.id_zona
JOIN    centro_astronomico c            ON c.id_centro   = z.id_centro
JOIN   (SELECT z2.id_centro, COUNT(DISTINCT o2.id_fenomeno) AS fenomenos_centro
          FROM observacion o2
          JOIN zona_observacion z2 ON z2.id_zona = o2.id_zona
         GROUP BY z2.id_centro) t       ON t.id_centro = c.id_centro
GROUP BY c.id_centro, c.nombre, f.tipo_clasificacion,
         COALESCE(s.tipo_evento, l.tipo_evento, ep.tipo_objeto, 'sin subtipo'),
         t.fenomenos_centro;

-- ---------------------------------------------------------------------
-- R8. Visitantes con mayor participación y valor total de las actividades
--     en que han reservado (solo visitantes con 8 o más reservas).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_r8_visitantes_participacion AS
SELECT  v.id_persona                                   AS id_visitante,
        CONCAT(p.nombre_pila, ' ', p.ap_paterno)       AS visitante,
        COUNT(r.id_reserva)                            AS reservas,
        SUM(r.asistencia_efectiva)                     AS asistencias,
        COUNT(DISTINCT c.id_centro)                    AS centros_distintos,
        SUM(a.valor)                                   AS valor_total_reservado
FROM    visitante v
JOIN    persona p               ON p.id_persona   = v.id_persona
JOIN    reserva r               ON r.id_visitante = v.id_persona AND r.estado = 'CONFIRMADA'
JOIN    actividad_observacion a ON a.id_actividad = r.id_actividad
JOIN    zona_observacion z      ON z.id_zona      = a.id_zona
JOIN    centro_astronomico c    ON c.id_centro    = z.id_centro
GROUP BY v.id_persona, p.nombre_pila, p.ap_paterno
HAVING  COUNT(r.id_reserva) >= 8;
