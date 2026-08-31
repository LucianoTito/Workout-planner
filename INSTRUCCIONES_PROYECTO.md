# Instrucciones del proyecto — Workout Planner

## Quién soy

Luciano Facundo Tito Cedrón. Backend developer jr. (.NET / C# / SQL Server) y
entusiasta de Python. Instructor certificado de CrossFit con más de 13 años de
experiencia. Trabajo y estudio en español, y el código y los comentarios también
van en español.

Este proyecto es mi planificador de entrenamiento: un CLI en Python que arma
planes periodizados y los exporta a Excel. Lo uso para mí y para mi novia (Brisa).

---

## Cómo trabajamos

**Antes de escribir código, pedime los archivos que necesites.** El repo tiene dos
motores independientes y es fácil tocar el equivocado. Si vas a modificar algo,
pedí el módulo y el YAML correspondiente en vez de inferir la estructura.

**No rompas el motor CrossFit.** `week_builder.py` y sus tests son territorio
estable. Los bloques nuevos van por el carril data-driven (`bloque_builder.py` +
`data/bloques/*.yaml`), que existe justamente para no tocarlo.

**Corré los tests antes de darme algo por terminado.** La suite completa son
cuatro archivos en `tests/`. Si agregás una feature, agregá sus tests. Y si los
tests son de reglas de seguridad, verificá que efectivamente fallen cuando se
rompe la regla, no que pasen por vacíos.

**Preferí data sobre código.** La gracia del diseño es que cambiar un plan no
requiera tocar Python. Si algo se puede resolver editando un YAML, se resuelve ahí.

---

## Arquitectura en dos carriles

| | Ciclo CrossFit | Bloques |
|---|---|---|
| Motor | `src/week_builder.py` | `src/bloque_builder.py` |
| Datos | `data/progresiones/*.yaml` + `config/atletas/*.yaml` | `data/bloques/*.yaml` |
| Cargas | calculadas por %RM del atleta | literales por semana en el YAML |
| Duración | 8 semanas | variable (4 en los actuales) |
| Exporter | `excel_exporter.py` | `bloque_exporter.py` (reusa los estilos) |

Ambos exportan al mismo formato de Excel: días como columnas, celdas combinadas
verticalmente cuando el texto es largo, y un área de NOTAS libre al final.
Temas de color: `rosa` (Brisa) y `arena` (yo).

### Esquema de un bloque

```yaml
meta:      # nombre, atleta, tema, total_semanas, semana_deload, nota_global, fases[]
dias:
  CLAVE:
    titulo: "DÍA X"
    subtitulo: "..."
    duracion: "~70-75 min"
    solo_en_variante: 5        # opcional: el día existe solo en esa variante
    secciones:
      - header: "..."
        items: [...]           # líneas fijas, iguales todas las semanas
        ejercicios:
          - nombre: "..."
            nota: "..."        # cue técnico fijo
            semanas: ["S1", "S2", "S3", "S4"]
variantes:                     # qué días salen según cuántos se entrene
  3: {dias: [...], descripcion: "..."}
variante_default: 4
```

Dos mecanismos avanzados, ambos usados en `reconstruccion.yaml`:
`componer:` arma un día fusionando secciones de otros días por referencia (no
duplica cargas), y `mover_a_e:` reubica secciones al día de accesorios en la
variante de 5 días. `recomposicion.yaml` no usa ninguno de los dos.

---

## Estado actual

Bloques en `data/bloques/`:

- **`reconstruccion.yaml`** — Bloque Reconstrucción, 4 semanas. Completado en
  agosto 2026. Se conserva como referencia; no lo modifiques.
- **`recomposicion.yaml`** — Bloque 1 · Recomposición, 4 semanas. **El activo.**
  Arrancó el 31/08/2026. Es el primero de cuatro bloques hasta el verano, con
  reevaluación cada 4 semanas.

El CLI (opción 4) escanea `data/bloques/` y deja elegir el bloque. No hay ningún
nombre de bloque hardcodeado.

---

## Contexto de entrenamiento que el YAML no explica

Estas son las razones detrás de las decisiones del bloque activo. Importan
porque si me sugerís cambios sin conocerlas, vas a sugerir cosas peligrosas.

### Prioridades, en orden

1. **Pérdida de grasa y recomposición corporal.** Siempre primero.
2. **Rodilla izquierda en óptimas condiciones**, sin dejar de entrenar.
3. **Recuperar masa muscular y fuerza.**

### Hombro derecho

Rotura parcial del supraespinoso con bursitis, confirmada por resonancia.

- **Fuera:** press de hombro y todas sus variantes (push press, jerk, thruster),
  vuelos laterales, press de banca, fondos, ring dips, muscle-ups.
- **Tolera bien:** landmine press, wall climbs, dominadas (estrictas y kipping),
  cruces en polea, push-ups, pushdown.
- **Regla importante:** *no asumas* qué ejercicios me molestan el hombro.
  Preguntame antes de afirmarlo. Hoy solo tengo pinchazos ocasionales al elevar
  los brazos sobre la cabeza fuera del gimnasio, y en entrenamiento no duele.

### Rodilla izquierda

Cirugías de ligamento cruzado y menisco, más artrosis. **El injerto se hizo con
isquiotibiales (semitendinoso)**, que es la causa estructural de la debilidad
del femoral izquierdo. Por eso el curl femoral lleva una serie extra del lado
izquierdo: el objetivo es reducir la brecha, no igualarla.

- Regla de "sin dolor" en todo momento.
- Tolera bien: wall balls, estocadas, sentadilla y bisagra con carga.
- Impacto limitado: box jumps y dobles por separado están bien, pero si se
  juntan en volumen alto en el mismo WOD, al día siguiente pincha.
- **Pistols fuera.**
- En todo trabajo unilateral: empiezo por la izquierda, y la derecha iguala las
  reps de la izquierda aunque pueda más.

### Logística

- Máximo 1:15 por sesión.
- Entre 3 y 5 sesiones por semana según trabajo y facultad. Los domingos son
  para mi familia: no entreno.
- Los WODs los elijo yo según los patrones ya trabajados en la semana. El plan
  fija el presupuesto (máximo 3 por semana, ninguno en día de Zona 2), no el
  contenido.
- Zona 2: mi rango es 111-130 ppm (33 años). Apunto a 120-130. Uso reloj con
  pulsómetro. Tengo remo, ski y assault bike.

---

## Reglas blindadas por tests

`tests/test_bloque_recomposicion.py` no solo verifica que el YAML parsee: hace
fallar el build si alguien rompe una regla de seguridad editando datos.

- El curl femoral izquierdo siempre lleva más series que el derecho.
- Todo ejercicio unilateral lleva el cue "IZQ primero".
- Los días de Zona 2 no pueden tener sección de WOD ni finisher.
- Nunca más de 3 sesiones con WOD por semana.
- Ningún día de fuerza puede prescribir press por encima de la cabeza, vuelos,
  press de banca ni fondos.

Si tocás el YAML del bloque activo, corré ese archivo antes de darlo por bueno.

---

## Estilo de los entregables

- **Excel:** una hoja por semana, días como columnas (no filas), celdas
  combinadas y centradas, fuente tamaño 12. Paleta arena: headers `#2B2B2B`,
  bandas doradas `#B8863B`, cremas `#F4ECDD`.
- **PDF:** una página por sesión, headers claros, tablas con series, reps,
  tempo, RPE y carga, y recordatorios al pie.
- Los Excel se guardan en Google Drive como pestañas de un Sheets maestro por
  atleta.

---

## En el horizonte

- Más bloques data-driven (hipertrofia, fuerza pura) reusando el mismo motor.
- Perfiles de atleta editables desde el CLI.
- Export a PDF además de Excel.
- Una versión C# / .NET + SQL Server de este planificador como posible proyecto
  final de la carrera (despriorizado por ahora).
