// 1. Solicitar permiso explícito al navegador para mostrar notificaciones estilo WhatsApp
        function pedirPermisoNotificaciones() { 
            if (!window.Notification) {
                alert("Este navegador no soporta notificaciones de escritorio.");
                return;
            }
            
            Notification.requestPermission().then(permission => {
                if (permission === "granted") {
                    alert("¡Notificaciones estilo WhatsApp activadas correctamente!");
                    // Lanzar una notificación de prueba en la esquina
                    new Notification("Don Nicolás", {
                        body: "Las alertas en la esquina de tu pantalla están listas.",
                        icon: "https://cdn-icons-png.flaticon.com/512/3233/3233483.png"
                    });
                } else {
                    alert("Has denegado los permisos de notificación en tu navegador.");
                }
            });
        }

        // 2. Disparar la notificación flotante en la esquina dentro de procesarYMostrarEvento
        function procesarYMostrarEvento(data) {
            let idUnico = data.id || `${data.tipo}-${data.mesa}-${data.mensaje || (data.items ? data.items.length : 0)}-${JSON.stringify(data.total || 0)}`;
            
            if (idsEventosProcesados.has(idUnico)) return;
            idsEventosProcesados.add(idUnico);

            contadorNotificaciones++;
            actualizarContadorVisual();
            reproducirSonidoAlerta();

            // --- LANZAR NOTIFICACIÓN NATIVA ESTILO WHATSAPP EN LA ESQUINA ---
            if (window.Notification && Notification.permission === "granted") {
                let tituloNoti = data.tipo === 'alerta' ? data.titulo : `🚀 Nuevo Pedido - Mesa #${data.mesa}`;
                let cuerpoNoti = data.tipo === 'alerta' ? data.mensaje : `Total a cobrar: Q ${data.total.toFixed(2)}`;
                
                let notificacionFlotante = new Notification(tituloNoti, {
                    body: cuerpoNoti,
                    icon: "https://cdn-icons-png.flaticon.com/512/3233/3233483.png",
                    tag: 'don-nicolas-alerta'
                });

                notificacionFlotante.onclick = function() {
                    window.focus();
                    notificacionFlotante.close();
                };
            }

            // Pintar la tarjeta en el monitor interno
            const contenedor = document.getElementById('contenedor-alertas');
            const mensajeVacio = document.getElementById('mensaje-vacio');
            if (mensajeVacio) mensajeVacio.remove();

            let tarjetaFlash = document.createElement('div');
            tarjetaFlash.className = 'notid-card p-3 mb-3';

            if (data.tipo === 'alerta') {
                tarjetaFlash.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <h5 class="m-0 fw-bold" style="color: var(--accent-gold);">${data.titulo}</h5>
                        <span class="badge bg-danger fs-6 px-3 py-1">Mesa #${data.mesa}</span>
                    </div>
                    <p class="mt-2 mb-2 text-dark">${data.mensaje}</p>
                    <div class="text-end">
                        <button class="btn btn-sm btn-outline-secondary py-0" onclick="marcarAtendido(this)">Marcar atendido</button>
                    </div>
                `;
            } else if (data.tipo === 'nuevo_pedido') {
                let itemsHtml = data.items.map(i => {
                    let detalles = '';
                    if (i.tamano) detalles += `<br><small class="text-secondary ms-3">📏 Tamaño: ${i.tamano}</small>`;
                    if (i.promo) detalles += `<br><small class="ms-3" style="color: var(--accent-gold);">🌅 Promo: ${i.promo}</small>`;
                    if (i.tipoLeche) detalles += `<br><small class="ms-3" style="color: var(--accent-gold);">🥛 Leche: ${i.tipoLeche}</small>`;
                    if (i.tipoEndulzante) detalles += `<br><small class="ms-3" style="color: var(--accent-gold);">🍯 Endulzante: ${i.tipoEndulzante}</small>`;
                    if (i.nota) detalles += `<br><small class="text-secondary ms-3">📝 Nota: ${i.nota}</small>`;
                    return `<li class="mb-2"><b>[${i.cliente || 'General'}]</b> ${i.cantidad || 1}x ${i.nombre} (Q ${(i.precio * (i.cantidad || 1)).toFixed(2)})${detalles}</li>`;
                }).join('');

                tarjetaFlash.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <h5 class="m-0 fw-bold" style="color: var(--accent-gold);">🚀 Nuevo Pedido</h5>
                        <span class="badge bg-success fs-6 px-3 py-1">Mesa #${data.mesa}</span>
                    </div>
                    <ul class="mt-2 mb-2 ps-3 text-dark small">${itemsHtml}</ul>
                    <div class="d-flex justify-content-between align-items-center mt-2 pt-2 border-top" style="border-color: var(--border-subtle) !important;">
                        <span class="fw-bold fs-6" style="color: var(--accent-gold);">Total: Q ${data.total.toFixed(2)}</span>
                        <button class="btn btn-sm btn-amber py-1" onclick="marcarAtendido(this)">Completar Pedido</button>
                    </div>
                `;
            }
            contenedor.prepend(tarjetaFlash);
        }
