// --- CARRITO DE COMPRAS Y GESTIÓN DE PEDIDOS ---
let carrito = [];

// Agregar productos al carrito desde el menú
function agregarAlCarrito(nombre, precio) {
    let itemExistente = carrito.find(item => item.nombre === nombre);
    if (itemExistente) {
        itemExistente.cantidad += 1;
    } else {
        carrito.push({ nombre: nombre, precio: precio, cantidad: 1 });
    }
    actualizarVistaCarrito();
}

// Modificar cantidad de un producto en el resumen
function cambiarCantidad(nombre, cambio) {
    let item = carrito.find(item => item.nombre === nombre);
    if (item) {
        item.cantidad += cambio;
        if (item.cantidad <= 0) {
            carrito = carrito.filter(i => i.nombre !== nombre);
        }
    }
    actualizarVistaCarrito();
}

// Renderizar la interfaz del carrito y actualizar totales
function actualizarVistaCarrito() {
    let contenedorLista = document.getElementById('lista-carrito');
    let contenedorPanel = document.getElementById('contenedor-resumen-pedido');
    let spanTotal = document.getElementById('total-carrito');

    if (!contenedorLista) return;

    if (carrito.length === 0) {
        contenedorPanel.style.display = 'none';
        contenedorLista.innerHTML = '';
        return;
    }

    contenedorPanel.style.display = 'block';
    contenedorLista.innerHTML = '';
    let totalGeneral = 0;

    carrito.forEach(item => {
        let subtotal = item.precio * item.cantidad;
        totalGeneral += subtotal;

        let divItem = document.createElement('div');
        divItem.className = 'd-flex justify-content-between align-items-center mb-2 pb-2 border-bottom border-secondary';
        divItem.innerHTML = `
            <div>
                <span class="text-light fw-bold" style="font-size: 0.85rem;">${item.nombre}</span><br>
                <small class="text-warning" style="font-size: 0.75rem;">Q ${item.precio.toFixed(2)} x ${item.cantidad}</small>
            </div>
            <div class="d-flex align-items-center gap-2">
                <span class="text-success fw-bold" style="font-size: 0.85rem;">Q ${subtotal.toFixed(2)}</span>
                <button class="btn btn-sm btn-outline-danger py-0 px-1" onclick="cambiarCantidad('${item.nombre}', -1)">-</button>
                <button class="btn btn-sm btn-outline-warning py-0 px-1" onclick="cambiarCantidad('${item.nombre}', 1)">+</button>
            </div>
        `;
        contenedorLista.appendChild(divItem);
    });

    spanTotal.innerText = `Q ${totalGeneral.toFixed(2)}`;
}

// --- ENVÍO DE PEDIDO AL SERVIDOR (Ruta relativa arreglada) ---
async function enviarPedido() {
    let totalGeneral = carrito.reduce((acc, item) => acc + (item.precio * item.cantidad), 0);

    try {
        let respuesta = await fetch('/api/enviar-pedido', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mesa: parseInt(numeroMesa),
                items: carrito,
                total: totalGeneral
            })
        });

        if (respuesta.ok) {
            alert("🚀 ¡Pedido enviado con éxito a la cocina!");
            carrito = [];
            actualizarVistaCarrito();
            // Desmarcar el checkbox de confirmación si existe
            let check = document.getElementById('checkRevisado');
            if (check) check.checked = false;
            let boton = document.getElementById('btn-enviar-pedido');
            if (boton) boton.disabled = true;
        } else {
            alert("Hubo un problema al procesar el pedido con el servidor.");
        }
    } catch (error) {
        console.error("Error de conexión:", error);
        alert("Error de conexión con el servidor.");
    }
}
