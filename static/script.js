let carrito = [];

function agregarAlCarrito(nombre, precio) {
    let encontrado = carrito.find(item => item.nombre === nombre);
    if (encontrado) {
        encontrado.cantidad += 1;
    } else {
        carrito.push({ nombre: nombre, precio: precio, cantidad: 1 });
    }
    actualizarCarritoUI();
}

function cambiarCantidad(index, cambio) {
    carrito[index].cantidad += cambio;
    if (carrito[index].cantidad <= 0) {
        carrito.splice(index, 1);
    }
    actualizarCarritoUI();
}

function actualizarCarritoUI() {
    let lista = document.getElementById("lista-carrito");
    let totalSpan = document.getElementById("total-carrito");
    let contenedorResumen = document.getElementById("contenedor-resumen-pedido");
    
    lista.innerHTML = "";
    
    if (carrito.length === 0) {
        contenedorResumen.style.display = "none";
        return;
    } else {
        contenedorResumen.style.display = "block";
    }

    let total = 0;
    carrito.forEach((item, index) => {
        let subtotal = item.precio * item.cantidad;
        total += subtotal;
        
        lista.innerHTML += `
            <div class="d-flex justify-content-between align-items-center py-2 border-bottom border-secondary">
                <div style="max-width: 55%;">
                    <h6 class="mb-0 text-light fw-bold" style="font-size: 0.95rem;">${item.nombre}</h6>
                    <small class="text-success">Q ${item.precio.toFixed(2)} c/u</small>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <button class="btn btn-sm btn-outline-warning py-0 px-2 fw-bold" onclick="cambiarCantidad(${index}, -1)">-</button>
                    <span class="text-warning fw-bold">${item.cantidad}</span>
                    <button class="btn btn-sm btn-outline-warning py-0 px-2 fw-bold" onclick="cambiarCantidad(${index}, 1)">+</button>
                    <button class="btn btn-sm text-danger ms-1 p-0" onclick="cambiarCantidad(${index}, -${item.cantidad})" title="Eliminar">🗑️</button>
                </div>
            </div>
        `;
    });
    totalSpan.innerText = `Q ${total.toFixed(2)}`;
}

async function enviarPedido() {
    if (carrito.length === 0) {
        alert("Por favor seleccione al menos un producto.");
        return;
    }

    let mesaActual = localStorage.getItem('mesa_actual') || 1;
    let totalCalculado = carrito.reduce((sum, item) => sum + (item.precio * item.cantidad), 0);

    let datosPedido = {
        mesa: parseInt(mesaActual),
        items: carrito,
        total: totalCalculado
    };

    try {
        let respuesta = await fetch('http://127.0.0.1:8000/api/enviar-pedido', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datosPedido)
        });

        let resultado = await respuesta.json();
        if (resultado.status === "success") {
            alert(`🎉 ¡Pedido enviado con éxito desde la Mesa #${mesaActual}! Nuestra cocina ha comenzado la preparación.`);
            carrito = [];
            actualizarCarritoUI();
        } else {
            alert("No se pudo conectar con el servidor.");
        }
    } catch (error) {
        alert("Error de conexión con el servidor.");
    }
}