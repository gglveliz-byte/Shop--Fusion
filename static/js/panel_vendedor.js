(() => {
  "use strict";

  /* ========= Helpers ========= */
  const $  = (sel, ctx=document) => ctx.querySelector(sel);
  const $$ = (sel, ctx=document) => Array.from(ctx.querySelectorAll(sel));
  const on = (el, ev, fn) => el && el.addEventListener(ev, fn);
  const csrfToken = () => {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  };

  const api = {
    base: "", // opcional, ej: "/api"
    headersJSON() {
      return {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken()
      };
    },
    async get(url) {
      const r = await fetch(url, { credentials: "same-origin" });
      if (!r.ok) throw new Error(`GET ${url} -> ${r.status}`);
      return r.json();
    },
    async post(url, data) {
      const r = await fetch(url, {
        method: "POST",
        headers: this.headersJSON(),
        credentials: "same-origin",
        body: JSON.stringify(data || {})
      });
      if (!r.ok) throw new Error(`POST ${url} -> ${r.status}`);
      return r.json();
    },
    async put(url, data) {
      const r = await fetch(url, {
        method: "PUT",
        headers: this.headersJSON(),
        credentials: "same-origin",
        body: JSON.stringify(data || {})
      });
      if (!r.ok) throw new Error(`PUT ${url} -> ${r.status}`);
      return r.json();
    },
    async del(url) {
      const r = await fetch(url, {
        method: "DELETE",
        headers: this.headersJSON(),
        credentials: "same-origin"
      });
      if (!r.ok) throw new Error(`DELETE ${url} -> ${r.status}`);
      return r.json();
    }
  };

  /* ========= Router (views) ========= */
  const views = $$(".view");
  const navLinks = $$(".nav-link");

  function showView(name){
    views.forEach(v => v.classList.toggle("is-active", v.dataset.view === name));
    navLinks.forEach(l => l.classList.toggle("is-active", l.dataset.view === name));
    // actualizar hash (opcional)
    if (location.hash !== `#${name}`) history.replaceState(null, "", `#${name}`);
  }

  function initRouter(){
    // Desde hash inicial
    const initial = (location.hash || "#dashboard").slice(1);
    if ($(`.view[data-view="${initial}"]`)) showView(initial); else showView("dashboard");

    // Clicks en sidebar
    navLinks.forEach(link => on(link, "click", (e) => {
      e.preventDefault();
      const view = link.dataset.view;
      showView(view);
    }));

    // Botón campana
    on($('[data-view="notificaciones"].btn-icon'), "click", () => showView("notificaciones"));
  }

  /* ========= Topbar: user menu & search ========= */
  function initTopbar(){
    const dd = $(".user-dropdown");
    if (!dd) return;
    const btn = $("button", dd);
    const menu = $(".menu", dd);

    on(btn, "click", () => {
      const open = menu.hasAttribute("hidden") ? false : true;
      menu.toggleAttribute("hidden", open);
      btn.setAttribute("aria-expanded", String(!open));
    });
    on(document, "click", (ev) => {
      if (!dd.contains(ev.target)) menu.setAttribute("hidden","")
    });

    on($(".topbar__search"), "submit", (e) => {
      e.preventDefault();
      // hook de búsqueda global (luego conectar)
      const q = e.currentTarget.q.value.trim();
      if (!q) return;
      console.log("[SEARCH]", q);
    });
  }

  /* ========= Toasts ========= */
  function initToasts(){
    $$(".toast .toast-close").forEach(b =>
      on(b, "click", (e) => e.currentTarget.closest(".toast").remove())
    );
  }

  /* ========= Modales ========= */
  const modals = $$(".modal");

  function openModal(sel){
    const dlg = $(sel);
    if (!dlg) return;
    // Si el navegador soporta <dialog>
    if (typeof dlg.showModal === "function") {
      dlg.showModal();
      // Aplicar estilo de pantalla completa en dispositivos pequeños
      if (window.innerWidth < 700) dlg.classList.add('mobile-full');
    } else {
      // Fallback: mostrar como bloque y añadir atributo open
      dlg.setAttribute('open','');
      if (window.innerWidth < 700) dlg.classList.add('mobile-full');
    }
  }
  function closeModal(dlg){
    if (!dlg) return;
    dlg.classList.remove('mobile-full');
    if (typeof dlg.close === "function") dlg.close(); else dlg.removeAttribute('open');
  }
  function initModals(){
    // abrir
    $$('[data-action="open-modal"]').forEach(btn => {
      on(btn, "click", () => openModal(btn.dataset.target));
    });
    // cerrar genérico
    $$('[data-action="close-modal"]').forEach(btn => {
      on(btn, "click", () => closeModal(btn.closest("dialog")));
    });
    // cerrar con ESC
    modals.forEach(dlg => on(dlg, "cancel", (e) => e.preventDefault() && closeModal(dlg)));
  }

  /* ========= Productos: modal form (solo hooks) ========= */
  function parseListFromInput(value){
    return value.split(",").map(s => s.trim()).filter(Boolean);
  }

  function renderImagePreviews(urls){
    const box = $("#prod-gallery");
    if (!box) return;
    box.innerHTML = "";
    urls.forEach(u => {
      const img = new Image();
      img.className = "prod-thumb";
      img.alt = "Imagen";
      img.src = u;
      box.appendChild(img);
    });
  }

  function renderVideoPreviews(urls){
    const box = $("#prod-video-previews");
    if (!box) return;
    box.innerHTML = "";
    urls.forEach(u => {
      // si es YouTube/Vimeo, solo mostramos link; si es mp4/webm, <video>
      if (/\.(mp4|webm)(\?.*)?$/i.test(u)) {
        const v = document.createElement("video");
        v.src = u; v.controls = true; v.width = 180;
        box.appendChild(v);
      } else {
        const a = document.createElement("a");
        a.href = u; a.target = "_blank";
        a.textContent = "Ver video";
        a.className = "btn-xxs";
        box.appendChild(a);
      }
    });
  }

  function initProductoModal(){
    const form = $("#form-producto");
    if (!form) return;

    // Previews reactivos
    on($("#prod-imagenes"), "input", (e) => renderImagePreviews(parseListFromInput(e.target.value)));
    on($("#prod-videos"), "input", (e) => renderVideoPreviews(parseListFromInput(e.target.value)));

    // Guardar (hook)
    on(form, "submit", async (e) => {
      e.preventDefault();
      const data = {
        id: $("#prod-id")?.value || null,
        titulo: $("#prod-titulo")?.value?.trim() || "",
        precio: parseFloat($("#prod-precio")?.value || "0"),
        categoria: $("#prod-categoria")?.value || "",
        estado: $("#prod-estado")?.value || "draft",
        descripcion: $("#prod-descripcion")?.value?.trim() || "",
        imagenes: parseListFromInput($("#prod-imagenes")?.value || ""),
        videos: parseListFromInput($("#prod-videos")?.value || "")
      };
      console.log("[SAVE PRODUCT] ->", data);

      // Aquí solo dejamos el hook; conecta luego a tu endpoint real:
      // const resp = await api.post("/vendedor/productos", data);
      // flashSuccess("Producto guardado");
      // closeModal($("#modal-producto"));
      // reloadProductos();

      closeModal($("#modal-producto"));
    });
  }

  /* ========= Productos: tabla (placeholder) ========= */
  function initProductosTable(){
    const tbody = $("#tbl-productos tbody");
    if (!tbody) return;

    // placeholder — luego haz GET a tu endpoint y llena filas
    tbody.innerHTML = "";
    // Ejemplo de fila dummy para ver estilos:
    const tpl = $("#tpl-product-row");
    if (tpl){
      const tr = tpl.content.cloneNode(true);
      tr.querySelector(".prod-thumb").src = "/static/images/placeholder.svg";
      tr.querySelector(".prod-name").textContent = "Producto demo";
      tr.querySelector(".prod-sku").textContent = "SKU-0001";
      tr.querySelector(".cell-price").textContent = "$ 10.00";
      tr.querySelector(".cell-category").textContent = "General";
      tr.querySelector(".cell-stock").textContent = "25";
      tr.querySelector(".cell-status").textContent = "Publicado";
      tbody.appendChild(tr);
    }

    // acciones editar/eliminar (hooks)
    on(tbody, "click", (e) => {
      const btn = e.target.closest("button[data-action]");
      if (!btn) return;
      const action = btn.dataset.action;
      if (action === "edit") {
        // cargar datos y abrir modal
        openModal("#modal-producto");
      } else if (action === "delete") {
        // confirmar y conectar a DELETE
        if (confirm("¿Eliminar este producto?")) {
          console.log("[DELETE PRODUCT]");
        }
      }
    });
  }

  /* ========= Inventario / Pedidos / Envíos (hooks vacíos) ========= */
  function initInventario(){ /* aquí luego GET /vendedor/inventario y bind de acciones */ }
  function initPedidos(){
    // Hook general de filtros
    on($("#order-filter-apply"), "click", () => {
      const status = $("#order-status")?.value;
      const from = $("#order-from")?.value;
      const to   = $("#order-to")?.value;
      console.log("[FILTER ORDERS]", {status, from, to});
      // GET /vendedor/pedidos?status=...&from=...&to=...
    });
  }
  function initEnvios(){}

  /* ========= Gráficas (solo toggles de rango) ========= */
  function initCharts(){
    const rangeSel = $("#sales-range");
    const from = $("#from-date");
    const to   = $("#to-date");
    const btn  = $("#btn-apply-range");

    function toggleCustom(){
      const custom = rangeSel.value === "custom";
      from.hidden = to.hidden = btn.hidden = !custom;
    }
    on(rangeSel, "change", toggleCustom);
    on(btn, "click", () => {
      console.log("[APPLY SALES RANGE]", {from: from.value, to: to.value});
      // GET /vendedor/ventas?from=...&to=... ó rango predefinido
    });
    toggleCustom();
  }

  /* ========= Notificaciones ========= */
  function initNotificaciones(){
    const list = $("#notif-list");
    const badge = $("#badge-notif");
    if (!list) return;

    // demo item
    const tpl = $("#tpl-notif-item");
    if (tpl){
      const li = tpl.content.cloneNode(true);
      li.querySelector(".notif-title").textContent = "Nuevo pedido #1024";
      li.querySelector(".notif-meta").textContent = "Hace 2 min • Total $45.90";
      list.appendChild(li);
      badge.hidden = false;
      badge.textContent = "1";
    }

    on(list, "click", (e) => {
      const btn = e.target.closest('[data-action="mark-read"]');
      if (!btn) return;
      btn.closest("li")?.remove();
      const n = Math.max(0, (+badge.textContent || 0) - 1);
      badge.textContent = String(n);
      if (n === 0) badge.hidden = true;
      // opcional: POST /vendedor/notificaciones/leido
    });
  }

  /* ========= Configuración: toggle método de pago ========= */
  function initConfig(){
    const sel = $("#cfg-metodo-pago");
    const bank = $(".bank-only");
    const paypal = $(".paypal-only");
    if (!sel || !bank || !paypal) return;
    function swap(){
      const v = sel.value;
      bank.hidden = (v !== "banco");
      paypal.hidden = (v !== "paypal");
    }
    on(sel, "change", swap);
    swap();
  }

  /* ========= Accesibilidad & variados ========= */
  function initA11y(){
    // Cerrar dropdown con ESC
    on(document, "keydown", (e) => {
      if (e.key === "Escape") {
        $$(".user-dropdown .menu").forEach(m => m.setAttribute("hidden",""));
        modals.forEach(d => d.open && d.close());
      }
    });
  }

  /* ========= Boot ========= */
  function boot(){
    initRouter();
    initTopbar();
    initToasts();
    initModals();
    initProductoModal();
    initProductosTable();
    initInventario();
    initPedidos();
    initEnvios();
    initCharts();
    initNotificaciones();
    initConfig();
    initA11y();
    console.log("%cPanel vendedor listo", "color:#6ea8fe");
  }

  document.readyState !== "loading" ? boot() : document.addEventListener("DOMContentLoaded", boot);
})();
