let html5QrCode = null;
let scanInProgress = false;
let scannerStarting = false;
window.currentItemId = null;

document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("searchInput");

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const query = searchInput.value.toLowerCase();

      document.querySelectorAll(".item-card").forEach(card => {
        card.style.display = card.innerText.toLowerCase().includes(query)
          ? "flex"
          : "none";
      });
    });
  }

  document.querySelectorAll(".item-card").forEach(card => {
    card.addEventListener("click", () => {
      const id = card.dataset.id;
      if (id) openItemModal(id);
    });
  });

  const params = new URLSearchParams(window.location.search);
  const openItemId = params.get("open_item");

  if (openItemId) {
    openItemModal(openItemId);
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  document.addEventListener("input", e => {
    if (e.target.id === "modalQtyInput") {
      const viewQty = document.getElementById("viewQty");
      if (viewQty) viewQty.innerText = e.target.value || "0";
      updateTotalRetailPreview();
    }

    if (e.target.id === "modalRetail") {
      updateTotalRetailPreview();
    }
  });
});

function formatCurrency(value) {
  return `$${(parseFloat(value) || 0).toFixed(2)}`;
}

function updateTotalRetailPreview() {
  const qtyInput = document.getElementById("modalQtyInput");
  const retailInput = document.getElementById("modalRetail");
  const totalRetailEl = document.getElementById("viewTotalRetail");

  if (!totalRetailEl) return;

  const qty = parseFloat(qtyInput?.value || 0);
  const retail = parseFloat(retailInput?.value || 0);

  totalRetailEl.innerText = formatCurrency(qty * retail);
}

function openItemModal(id) {
  window.currentItemId = id;

  const modal = document.getElementById("itemModal");
  if (!modal) return;

  modal.style.display = "flex";

  fetch(`/item/${id}`)
    .then(res => res.json())
    .then(data => {
      const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.innerText = value ?? "";
      };

      const setValue = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.value = value ?? "";
      };

      setText("modalName", data.name);
      setText("modalSku", data.sku);
      setText("viewManufacturer", data.manufacturer);
      setText("viewDimensions", data.dimensions);
      setText("viewColors", data.colorways);
      setText("viewWeight", data.weight);
      setText("viewCost", formatCurrency(data.cost_price));
      setText("viewRetail", formatCurrency(data.retail_price));
      setText("viewQty", data.quantity);
      setText("viewTotalRetail", formatCurrency(data.total_retail_value));

      setValue("modalManufacturer", data.manufacturer);
      setValue("modalDimensions", data.dimensions);
      setValue("modalColors", data.colorways);
      setValue("modalCost", data.cost_price);
      setValue("modalRetail", data.retail_price);
      setValue("modalQtyInput", data.quantity);
      setValue("modalWeight", data.weight);

      const modalImage = document.getElementById("modalImage");
      const modalBarcode = document.getElementById("modalBarcode");

      if (modalImage) {
        modalImage.src = data.image_path || "/static/placeholder.png";
      }

      if (modalBarcode) {
        modalBarcode.src = data.barcode_path || "";
      }

      const labelBtn = document.getElementById("generateLabelBtn");
      if (labelBtn) {
        labelBtn.onclick = () => {
          window.location.href = `/labels/item/${data.id}`;
        };
      }

      const deleteForm = document.getElementById("deleteForm");
      if (deleteForm) {
        deleteForm.action = `/delete-item/${data.id}`;
      }

      const updateImageForm = document.getElementById("updateImageForm");
      if (updateImageForm) {
        updateImageForm.action = `/item/${data.id}/update-image`;
      }

      resetEditMode();
      updateTotalRetailPreview();
    })
    .catch(err => {
      console.error("openItemModal error:", err);
    });
}

function closeItemModal() {
  const modal = document.getElementById("itemModal");
  if (modal) modal.style.display = "none";
}

function toggleEditMode() {
  const editing = document.body.classList.toggle("editing");

  document.querySelectorAll(".edit-field").forEach(el => {
    el.style.display = editing ? "block" : "none";
  });

  document.querySelectorAll(".field p").forEach(el => {
    el.style.display = editing ? "none" : "block";
  });

  const saveBtn = document.getElementById("saveBtn");
  if (saveBtn) saveBtn.style.display = editing ? "inline-flex" : "none";

  updateTotalRetailPreview();
}

function resetEditMode() {
  document.body.classList.remove("editing");

  document.querySelectorAll(".edit-field").forEach(el => {
    el.style.display = "none";
  });

  document.querySelectorAll(".field p").forEach(el => {
    el.style.display = "block";
  });

  const saveBtn = document.getElementById("saveBtn");
  if (saveBtn) saveBtn.style.display = "none";
}

function saveItemChanges() {
  if (!window.currentItemId) return;

  const modalManufacturer = document.getElementById("modalManufacturer");
  const modalDimensions = document.getElementById("modalDimensions");
  const modalColors = document.getElementById("modalColors");
  const modalCost = document.getElementById("modalCost");
  const modalRetail = document.getElementById("modalRetail");
  const modalWeight = document.getElementById("modalWeight");

  const viewManufacturer = document.getElementById("viewManufacturer");
  const viewDimensions = document.getElementById("viewDimensions");
  const viewColors = document.getElementById("viewColors");
  const viewCost = document.getElementById("viewCost");
  const viewRetail = document.getElementById("viewRetail");
  const viewWeight = document.getElementById("viewWeight");

  fetch(`/edit-item/${window.currentItemId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      manufacturer: modalManufacturer?.value || "",
      dimensions: modalDimensions?.value || "",
      colorways: modalColors?.value || "",
      cost_price: modalCost?.value || "",
      retail_price: modalRetail?.value || "",
      weight: modalWeight?.value || ""
    })
  })
    .then(res => res.json())
    .then(() => {
      if (viewManufacturer && modalManufacturer) {
        viewManufacturer.innerText = modalManufacturer.value;
      }

      if (viewDimensions && modalDimensions) {
        viewDimensions.innerText = modalDimensions.value;
      }

      if (viewColors && modalColors) {
        viewColors.innerText = modalColors.value;
      }

      if (viewCost && modalCost) {
        viewCost.innerText = formatCurrency(modalCost.value);
      }

      if (viewRetail && modalRetail) {
        viewRetail.innerText = formatCurrency(modalRetail.value);
      }

      if (viewWeight && modalWeight) {
        viewWeight.innerText = modalWeight.value;
      }

      updateTotalRetailPreview();
      resetEditMode();
    })
    .catch(err => {
      console.error("saveItemChanges error:", err);
    });
}

function adjustQty(change) {
  if (!window.currentItemId) return;

  fetch(`/adjust-quantity/${window.currentItemId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ change })
  })
    .then(res => res.json())
    .then(data => {
      const viewQty = document.getElementById("viewQty");
      const modalQtyInput = document.getElementById("modalQtyInput");

      if (viewQty) viewQty.innerText = data.new_quantity;
      if (modalQtyInput) modalQtyInput.value = data.new_quantity;

      updateTotalRetailPreview();
    })
    .catch(err => {
      console.error("adjustQty error:", err);
    });
}

function openScanner() {
  const modal = document.getElementById("scannerModal");
  const scannerEl = document.getElementById("scanner");

  if (!modal || !scannerEl) {
    console.error("Scanner modal or scanner element not found");
    return;
  }

  if (scannerStarting) return;

  scannerStarting = true;
  modal.style.display = "flex";
  scanInProgress = false;

  setTimeout(async () => {
    try {
      if (html5QrCode) {
        try {
          await html5QrCode.stop();
        } catch (_) {}

        try {
          await html5QrCode.clear();
        } catch (_) {}

        html5QrCode = null;
      }

      html5QrCode = new Html5Qrcode("scanner");

      await html5QrCode.start(
        { facingMode: "environment" },
        {
          fps: 14,
          qrbox: { width: 300, height: 120 }
        },
        decodedText => {
          console.log("DECODED:", decodedText);
          handleScannedCode(decodedText);
        },
        () => {}
      );

      console.log("Scanner started successfully");
    } catch (err) {
      console.error("Scanner failed to start:", err);
      alert("Scanner failed to start. Check console.");
    } finally {
      scannerStarting = false;
    }
  }, 50);
}

async function closeScanner() {
  const modal = document.getElementById("scannerModal");
  if (modal) modal.style.display = "none";

  scanInProgress = false;

  if (html5QrCode) {
    try {
      await html5QrCode.stop();
    } catch (_) {}

    try {
      await html5QrCode.clear();
    } catch (_) {}

    html5QrCode = null;
  }
}

function handleScannedCode(text) {
  if (scanInProgress) return;

  scanInProgress = true;

  const cleanText = text.trim();
  console.log("SCANNED CLEAN TEXT:", cleanText);

  fetch(`/scan/${encodeURIComponent(cleanText)}`)
    .then(res => res.json())
    .then(async data => {
      console.log("SCAN RESPONSE:", data);

      await closeScanner();

      if (!data.found) {
        alert(`Scanned "${cleanText}" but no matching item was found.`);
        scanInProgress = false;
        return;
      }

      const itemCard = document.querySelector(`.item-card[data-id="${data.id}"]`);

      if (itemCard) {
        openItemModal(data.id);
      } else {
        window.location.href = `/?open_item=${data.id}`;
      }

      setTimeout(() => {
        scanInProgress = false;
      }, 1000);
    })
    .catch(async err => {
      console.error("SCAN FETCH ERROR:", err);
      alert("Decoded barcode, but lookup failed.");

      await closeScanner();
      scanInProgress = false;
    });
}