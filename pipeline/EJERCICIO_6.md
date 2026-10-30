# Integracion de resultados aprobados con el tablero

La seccion Pronosticos consulta el resultado autorizado del pipeline. Las demas
secciones mantienen los datos descriptivos del laboratorio 10. No se usan sus
predicciones heredadas cuando no hay una aprobacion del pipeline nuevo.

## 6.1 Version aprobada y metadatos

La pagina lee `publicaciones/vigente.json` en el servidor. Este indicador apunta
a `versiones/<version>.json` e incluye la huella del archivo. El lector verifica
la huella antes de utilizar el contenido y exige que la version este aprobada.
Tambien comprueba fechas, cantidades finitas, consistencia de los metadatos y
que MAE y RMSE correspondan a los meses mostrados.

Cada registro mensual de una version aprobada contiene los siguientes campos.

| Campo | Contenido |
| --- | --- |
| destino | Guatemala |
| fecha | Mes estimado, en formato AAAA-MM-01 |
| valor | Llegadas mensuales estimadas |
| unidad | llegadas_por_mes |
| id_ejecucion | Identificador del run de MLflow, o de la exportacion local si se ejecuto individualmente |
| fecha_generacion | Fecha y hora con zona horaria |
| version_procedimiento | Identificador de la version que conserva configuracion y trazabilidad |

El archivo tambien conserva el periodo global y los datos de validacion.
`tipo_identificador` aclara si se utilizo MLflow o una exportacion local.
Cuando ejecuta el orquestador se conserva el run real, sin crear uno ficticio.

La ruta predeterminada es `pipeline/data/processed/publicaciones`, relativa al
repositorio. Se puede cambiar mediante `TURISMO_PUBLICACIONES_DIR` en el
servidor de Next.js. Si se personaliza `rutas.publicaciones` en el TOML, debe
indicarse la misma carpeta en esa variable. El valor no se envia al navegador.
No se necesitan rutas personales ni ejecutar el modelo para consultar archivos.

La pagina se renderiza por solicitud mediante `connection()` de Next.js. La
version no queda congelada al construir la aplicacion. El boton Consultar
actualizacion solicita nuevamente los datos, sin entrenar ni ejecutar Python.

## 6.2 Observaciones, estimaciones y validacion

La vista aprobada distingue Observado en la base de Estimacion aprobada.
El grafico utiliza una linea continua para lo observado y una discontinua para
lo estimado, ademas de colores y etiquetas diferentes. La tabla mantiene las
mismas denominaciones. No se depende solamente del color para distinguirlas.

Se muestran la fecha de generacion en horario de Guatemala, MAE, RMSE y el
periodo evaluado. MAE se explica como la diferencia absoluta promedio entre
estimacion y observacion. RMSE se explica como una medida que da mas peso a
errores grandes. Ambos se expresan en llegadas por mes.

Cambiar entre grafico y tabla modifica solo la presentacion. Las metricas
siguen correspondiendo a todos los meses de validacion de esa version. No se
recalculan ni se presenta el error de un periodo distinto. Las cifras se
redondean para lectura, conservando la precision en el archivo original.

No se agregan MAPE, intervalos de confianza o bandas de error que no hayan sido
calculados y certificados en el pipeline. Tampoco se muestran modelos o series
que no pertenecen a la version aprobada.

## 6.3 Limites y orientacion a decisiones

La interfaz advierte que las cifras son academicas y no oficiales, que los
meses mostrados ya tienen valores reportados para comparar y que esta
evaluacion no es una proyeccion de meses futuros. Aclara que el error medido
no garantiza el desempeno posterior ni reconstruye exactamente la informacion
que estaba disponible en tiempo real.

Los parametros SARIMA, identificadores, rutas y huellas se conservan en los
archivos y en MLflow, sin mostrarse como controles o explicaciones del tablero.
El navegador recibe solo los datos agregados necesarios para la consulta.
Se mantuvieron la paleta y las fuentes del tablero existente.

## 6.4 Actualizacion segura y ausencia de resultados

La etapa 7 guarda y verifica la version antes de activar `vigente.json`. El
cambio del indicador se realiza de forma atomica. Una candidata rechazada o
un error previo a la activacion no sustituyen la version que ya estaba aprobada.
El lector solo utiliza el indicador, por lo que conservar archivos candidatos
o reportes nuevos no cambia lo que muestra el tablero.

Si no existe una primera version aprobada, se muestra Estimaciones no
disponibles. No se inventan ceros ni se utilizan las predicciones anteriores
del laboratorio 10 como alternativa. Este es el estado actual de los datos
reales, porque SARIMA no supero la referencia.

Si existe un indicador pero su archivo no puede verificarse, se muestra una
indisponibilidad temporal. Esto se distingue de un rechazo de candidata, que
mantiene el indicador anterior intacto. Una alteracion externa de un archivo
ya aprobado no se oculta mostrando datos sin comprobar.

## Comprobaciones realizadas

- Las 70 pruebas Python incluyen una publicacion sintetica con el pipeline real
  y su lectura desde el modulo del tablero. Se verifico compatibilidad entre
  el archivo que escribe Python y el lector de Node.js.
- Las 15 pruebas del lector comprueban ausencia de indicador, lectura aprobada,
  integridad, metadatos, meses incompletos o repetidos, valores invalidos,
  metricas inconsistentes y rutas fuera de la carpeta permitida.
- Una candidata rechazada conserva la lectura anterior. Una nueva version
  aprobada se consulta sin memoria de una version anterior.
- La revision del navegador mostro el estado real sin estimaciones aprobadas.
  En un servidor separado, con datos sinteticos y una advertencia visible,
  se comprobaron grafico, tabla, metricas, fecha, limites y actualizacion.
- Consultar la actualizacion mantuvo el numero de runs de MLflow en cinco,
  igual que antes de la prueba. No se ejecuto nuevamente el modelo.

La carpeta sintetica fue temporal y estuvo separada de publicaciones reales.
No se aprobo el SARIMA real ni se modificaron los CSV originales. La evidencia
queda en `data/processed/evidencia_tablero.json` y las capturas
`ejercicio_6_sin_aprobacion.jpg` y `ejercicio_6_aprobada_sintetica.jpg`.

## Comandos

Desde la raiz del repositorio:

```bash
pnpm test:publicaciones
pnpm run validate
pnpm build --webpack
pnpm start
```

Con el entorno Python activado:

```bash
python -m unittest discover -s pipeline/tests -v
```

La compilacion de produccion se verifico con Webpack porque Turbopack encontro
una restriccion del entorno al abrir un proceso interno de CSS. No se modifico
la tipografia ni la configuracion de compilacion del proyecto para evitarlo.
El despliegue con Docker y los comandos de restauracion corresponden a los
siguientes ejercicios.
