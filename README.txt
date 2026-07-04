Pokemon Finder Deluxe

Pokemon Finder Deluxe es una herramienta que armamos para escanear tu pantalla (viene bárbaro si estás jugando en un emulador o un juego de PC). Lo que hace es leer los textos del juego, reconocer los nombres de los Pokémon automáticamente y abrirte la información detallada directo en tu navegador.

Tiene un sistema inteligente que va aprendiendo de sus propios errores y te deja configurar varias zonas de lectura en la pantalla, adaptándose a la interfaz de cualquier juego.

---

## Cómo usar el programa

### 1. Marcar dónde leer (usando F8)
Para que el programa sepa dónde tiene que mirar, primero le tenés que marcar la zona de los diálogos:
* Abrí el juego y dejalo a la vista.
* Tocá la tecla F8 (o dale clic al botón de "Nueva caja de diálogo" en el menú).
* Vas a ver que la pantalla se oscurece un poco. Ahí hacé clic y arrastrá el mouse para dibujar un rectángulo justo arriba de la caja de texto del juego.
* Cuando sueltes el clic, te va a pedir que toques una tecla (puede ser la Q, el 1, F4, la que te quede más cómoda). Esa va a ser tu tecla rápida de captura para esa zona.
* Podés repetir esto las veces que quieras si el juego tiene textos en distintos lados.

### 2. Capturar y buscar automáticamente
* Una vez que marcaste las zonas, podés minimizar el programa y ponerte a jugar tranquilo.
* Cuando veas que aparece el nombre de un Pokémon, simplemente tocá la tecla que elegiste en el paso anterior.
* El programa saca una captura invisible, lee el texto, se da cuenta de qué Pokémon es y te abre la ficha en tu navegador web de forma automática.

### 3. El programa aprende de sus errores
A veces, la letra del juego es rara o el fondo confunde a la cámara. Por eso el sistema está preparado para que lo corrijas:
* Si duda: Si el programa lee algo raro y no sabe si es, por ejemplo, "Mew" o "Mewtwo", te va a saltar una ventanita preguntando cuál es el correcto. Vos elegís y ya se lo guarda para la próxima vez.
* Corregir a mano: Si se equivocó de Pokémon o directamente no detectó nada, andá al programa y tocá en "Corregir Última Captura". Ahí le escribís el nombre correcto y el sistema asocia esa lectura fallida con el Pokémon real, así no le vuelve a pasar.
* Revisar la memoria: En la opción de "Gestionar Decisiones Aprendidas" podés ver, editar o borrar todas las correcciones manuales que le fuiste enseñando con el tiempo.

---

## Detalles que suman

* Funciona de fondo: El programa detecta las teclas que tocás aunque estés jugando a pantalla completa. No hace falta que tengas la ventana del buscador activa.
* Se actualiza solo: Si hay una versión nueva publicada en GitHub, el programa te avisa y se baja la actualización de forma automática, sin que pierdas tus configuraciones ni tus zonas guardadas.
* No se olvida de nada: Todas las zonas que armás y las correcciones que le enseñás quedan guardadas en tu compu. Cuando lo vuelvas a abrir, ya está todo listo para usar.

---

### Un aviso importante antes de empezar
Para que el programa pueda leer el texto de la pantalla, necesitás tener instalado el motor Tesseract-OCR en tu computadora (suele instalarse en rutas como C:\Program Files\Tesseract-OCR\tesseract.exe). Si no lo tenés, la lectura automática no va a funcionar.