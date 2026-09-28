# INSTRUCCIONES DEL PROYECTO — WORKOUT PLANNER

---

## 1. Quién soy y en qué idioma trabajamos

Luciano Facundo Tito Cedrón. Backend developer jr. (.NET / C# / SQL Server) y
entusiasta de Python. Instructor certificado de CrossFit con más de 13 años de
experiencia.

**Todo en español:** las respuestas, el código, los comentarios, los nombres de
variables y los textos de los YAML.

Este proyecto es mi planificador de entrenamiento: un CLI en Python que arma
planes periodizados y los exporta a Excel. Lo uso para mí y para mi novia (Brisa).

---

## 2. Cómo trabajar conmigo acá

**Pedime los archivos que necesites antes de escribir código.** El repo tiene dos
motores independientes y es fácil inferir mal una estructura. Si vas a tocar algo,
pedí el módulo y el YAML correspondiente en vez de adivinar el esquema.

**Cuando pido un cambio, detallá exactamente qué archivo vamos a tocar y por qué.**
No hagas cambios sin confirmar primero.

**Código antes de ejecutar.** Cuando modifiques un archivo, mostrame el cambio
para que lo revise antes de que lo grabes.

**Paso a paso.** Si el cambio es largo, hacelo en bloques chicos y confirmá cada
uno antes de seguir.

**Tests después de tocar `src/`.** Corré el que corresponda al carril que tocaste,
o los cinco si no estás seguro:

```bash
python tests/test_week_builder.py           # motor CrossFit
python tests/test_rm_calculator.py          # cálculo %RM → kg
python tests/test_bloque_reconstruccion.py  # bloque viejo (regresión)
python tests/test_bloque_recomposicion.py   # bloque activo
python tests/test_cli_dias_bloque.py        # pantalla de días del menú 4
```

Si algo falla, lo vemos juntos. No lo arregles cambiando el test.

**Excel de prueba.** Cuando toquemos tipografía, colores o layout, generá una
semana de ejemplo y mostrame cómo quedó.

**Preferí data sobre código.** La gracia del diseño es que cambiar un plan no
requiera tocar Python. Si se puede resolver editando un YAML, se resuelve ahí.

---

## 3. Qué NO hacer sin preguntar

- Tocar `main.py`. Decime primero qué cambio proponés.
- Tocar el motor CrossFit (`week_builder.py`, `progression_loader.py`,
  `rm_calculator.py`, `core_selector.py`). Es territorio estable.
- **Editar `data/bloques/recomposicion.yaml`.** Es el bloque activo y contiene
  restricciones médicas. Ver sección 6.
- Modificar tests existentes. Crear archivos de test nuevos sí es libre.
- Agregar librerías nuevas.

## 4. Qué SÍ hacer libremente

- Editar los YAML de progresiones (`data/progresiones/*.yaml`).
- Ajustar colores, fuentes y alturas en `excel_exporter.py` (después me mostrás).
- Crear archivos de test nuevos para features nuevas.
- Revisar o explicar código si lo pido.
- Sugerir mejoras y refactors. Primero la propuesta, después el código.

---

## 5. Arquitectura: dos carriles independientes

| | Ciclo CrossFit | Bloques |
|---|---|---|
| Motor | `src/week_builder.py` | `src/bloque_builder.py` |
| Datos | `data/progresiones/*.yaml` + `config/atletas/*.yaml` | `data/bloques/*.yaml` |
| Cargas | calculadas por %RM del atleta | literales por semana en el YAML |
| Duración | 8 semanas | variable (4 en los actuales) |
| Exporter | `excel_exporter.py` | `bloque_exporter.py` (reusa los estilos) |

El carril de bloques existe justamente para no tocar el motor CrossFit. Todo
bloque nuevo va por ahí.

Ambos exportan al mismo formato: días como columnas, celdas combinadas
verticalmente cuando el texto es largo, área de NOTAS libre al final. Temas de
color: `rosa` (Brisa) y `arena` (yo).

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

Dos mecanismos avanzados, ambos usados en `reconstruccion.yaml`: `componer:`
arma un día fusionando secciones de otros días por referencia (no duplica
cargas), y `mover_a_e:` reubica secciones al día de accesorios en la variante de
5 días. `recomposicion.yaml` no usa ninguno de los dos.

### Bloques existentes

- **`reconstruccion.yaml`** — Bloque Reconstrucción, 4 semanas. Completado en
  agosto 2026. Se conserva como referencia. No lo modifiques.
- **`recomposicion.yaml`** — Bloque 1 · Recomposición, 4 semanas. **El activo.**
  Arrancó el 31/08/2026. Primero de cuatro bloques hasta el verano, con
  reevaluación cada 4 semanas.

El CLI (opción 4) escanea `data/bloques/` y deja elegir. No hay nombres de
bloque hardcodeados.

---

## 6. Contexto de entrenamiento — leer antes de sugerir ejercicios

Estas son las razones detrás de las decisiones del bloque activo. Importan
porque si sugerís cambios sin conocerlas, vas a sugerir cosas peligrosas.

### Prioridades, en orden

1. **Pérdida de grasa y recomposición corporal.** Siempre primero.
2. **Rodilla izquierda en óptimas condiciones**, sin dejar de entrenar.
3. **Recuperar masa muscular y fuerza.**

### Hombro derecho

Rotura parcial del supraespinoso con bursitis, confirmada por resonancia.

- **Fuera:** press de hombro y todas sus variantes (push press, jerk, thruster),
  vuelos laterales, press de banca, fondos, ring dips, muscle-ups.
- **Tolera bien (confirmado 31/08/2026):** landmine press, wall climbs, dominadas
  (estrictas y kipping), cruces en polea, push-ups, pushdown, dragon flag,
  ab roll-out, kb dead bug pullover, overhead kb carry, overhead walk.
- **Con límite:** el face pull va solo con tensión muy baja. Con más tensión
  pincha. El serrato punch sí se puede progresar.
- **Borderline, fuera por ahora:** One Arm OH Kb Sit up.
- **Regla importante:** *no asumas* qué ejercicios me molestan el hombro.
  Preguntame antes de afirmarlo. Hoy solo tengo pinchazos ocasionales al elevar
  los brazos sobre la cabeza fuera del gimnasio; entrenando no duele.

### Rodilla izquierda

Cirugías de ligamento cruzado y menisco, más artrosis. **El injerto se hizo con
isquiotibiales (semitendinoso)**, que es la causa estructural de la debilidad del
femoral izquierdo. Por eso el curl femoral lleva una serie extra del lado
izquierdo: el objetivo es reducir la brecha, no igualarla.

- Regla de "sin dolor" en todo momento.
- Tolera bien: wall balls, estocadas, sentadilla y bisagra con carga.
- Impacto limitado: box jumps y dobles por separado están bien, pero si se juntan
  en volumen alto en el mismo WOD, al día siguiente pincha.
- **Pistols fuera.**
- En todo trabajo unilateral: empiezo por la izquierda, y la derecha iguala las
  reps de la izquierda aunque pueda más.

### Logística

- Máximo 1:15 por sesión.
- Entre 3 y 5 sesiones por semana según trabajo y facultad. Los domingos son para
  mi familia: no entreno.
- Los WODs los elijo yo según los patrones ya trabajados en la semana. El plan
  fija el presupuesto (máximo 3 por semana, ninguno en día de Zona 2), no el
  contenido.
- Zona 2: mi rango es 111-130 ppm (33 años). Apunto a 120-130. Uso reloj con
  pulsómetro. Tengo remo, ski y assault bike.

---

## 7. Reglas blindadas por tests

`tests/test_bloque_recomposicion.py` no solo verifica que el YAML parsee: hace
fallar el build si alguien rompe una regla de seguridad editando datos.

- El curl femoral izquierdo siempre lleva más series que el derecho.
- Todo ejercicio unilateral lleva el cue "IZQ primero".
- Los días de Zona 2 no pueden tener sección de WOD ni finisher.
- Nunca más de 3 sesiones con WOD por semana.
- Ningún día de fuerza puede prescribir press por encima de la cabeza, vuelos,
  press de banca ni fondos.

Si tocás el YAML del bloque activo, corré ese archivo antes de darlo por bueno.
Si un cambio hace fallar uno de estos tests, **el problema es el cambio, no el
test.**

---

## 8. Estilo de los entregables

- **Excel:** una hoja por semana, días como columnas (no filas), celdas
  combinadas y centradas, fuente tamaño 12. Paleta arena: headers `#2B2B2B`,
  bandas doradas `#B8863B`, cremas `#F4ECDD`.
- **PDF:** una página por sesión, headers claros, tablas con series, reps, tempo,
  RPE y carga, recordatorios al pie.
- Los Excel se guardan en Google Drive como pestañas de un Sheets maestro por
  atleta.

---

## 9. Cómo reportar cuando terminás algo

Decime siempre:

- Qué archivo modificaste.
- Qué cambió y por qué.
- Si hay que testear algo específico.
- Si quedó en borrador o listo para usar.

---

## 10. En el horizonte

- Más bloques data-driven (hipertrofia, fuerza pura) reusando el mismo motor.
- Perfiles de atleta editables desde el CLI.
- Export a PDF además de Excel.
- Una versión C# / .NET + SQL Server de este planificador como posible proyecto
  final de la carrera (despriorizado por ahora).
