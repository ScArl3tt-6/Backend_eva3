// ============================================================
// static/js/app.js — COMPORTAMIENTO GLOBAL DEL SITIO
// Responsabilidad: cerrar automáticamente los mensajes flash de
// éxito/información (marcados con data-autocerrar en
// parciales/mensajes.html) para que no queden estorbando la
// pantalla. Los de error y advertencia se quedan hasta que la
// persona los cierre a mano.
// ============================================================
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("[data-autocerrar]").forEach(function (aviso) {
    setTimeout(function () {
      const instancia = bootstrap.Alert.getOrCreateInstance(aviso);
      instancia.close();
    }, 8000);
  });
});
