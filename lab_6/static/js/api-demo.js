
"use strict";

// ======================================
// НАЛАШТУВАННЯ API
// ======================================

const API_URL = "/api/v1/products";

const form = document.getElementById("product-form");
const productIdInput = document.getElementById("product-id");
const nameInput = document.getElementById("name");
const categoryInput = document.getElementById("category");
const priceInput = document.getElementById("price");
const imageInput = document.getElementById("image");
const descriptionInput = document.getElementById("description");

const productsList = document.getElementById("products-list");
const productsCount = document.getElementById("products-count");
const notification = document.getElementById("notification");
const loading = document.getElementById("loading");

const submitButton = document.getElementById("submit-button");
const cancelButton = document.getElementById("cancel-button");
const refreshButton = document.getElementById("refresh-button");
const formTitle = document.getElementById("form-title");

let products = [];

// ======================================
// ПОВІДОМЛЕННЯ
// ======================================

function showNotification(message, type = "success") {
    notification.textContent = message;

    notification.className =
        "mb-6 rounded-xl px-5 py-4 font-medium border " +
        (type === "success"
            ? "bg-emerald-50 border-emerald-300 text-emerald-900"
            : "bg-red-50 border-red-300 text-red-800");
}

// ======================================
// HTTP-ЗАПИТИ
// ======================================

async function apiRequest(url, options = {}) {
    let response;

    try {
        response = await fetch(url, {
            credentials: "same-origin",
            ...options
        });
    } catch (error) {
        throw new Error("Не вдалося з'єднатися із сервером.");
    }

    let data;

    try {
        data = await response.json();
    } catch (error) {
        throw new Error(
            "Сервер повернув некоректну відповідь. Перевірте авторизацію."
        );
    }

    if (!response.ok || data?.success === false) {
        throw new Error(
            data?.error || `Помилка HTTP ${response.status}`
        );
    }

    return data;
}

// ======================================
// СТВОРЕННЯ HTML-ЕЛЕМЕНТІВ
// ======================================

function createElement(tag, className = "", text = "") {
    const element = document.createElement(tag);
    element.className = className;
    element.textContent = text;
    return element;
}

// ======================================
// СКИДАННЯ ФОРМИ
// ======================================

function resetForm() {
    form.reset();

    productIdInput.value = "";
    formTitle.textContent = "Додати товар";
    submitButton.textContent = "Додати товар";
    cancelButton.classList.add("hidden");
}

// ======================================
// РЕДАГУВАННЯ ТОВАРУ
// ======================================

function startEdit(product) {
    productIdInput.value = product.id;
    nameInput.value = product.name;
    categoryInput.value = product.category;
    priceInput.value = product.price;
    imageInput.value = product.image;
    descriptionInput.value = product.description;

    formTitle.textContent = `Редагувати товар #${product.id}`;
    submitButton.textContent = "Зберегти зміни";

    cancelButton.classList.remove("hidden");

    form.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

// ======================================
// ВИДАЛЕННЯ ТОВАРУ
// ======================================

async function deleteProduct(product) {
    if (!confirm(`Видалити товар "${product.name}"?`)) {
        return;
    }

    try {
        await apiRequest(`${API_URL}/${product.id}`, {
            method: "DELETE"
        });

        showNotification("Товар успішно видалено.");
        resetForm();
        await loadProducts();

    } catch (error) {
        showNotification(error.message, "error");
    }
}

// ======================================
// ВІДОБРАЖЕННЯ ТОВАРІВ
// ======================================

function renderProducts() {
    productsList.replaceChildren();
    productsCount.textContent = products.length;

    if (products.length === 0) {
        productsList.appendChild(
            createElement(
                "p",
                "text-gray-500 text-center py-10",
                "У базі даних поки немає товарів."
            )
        );
        return;
    }

    for (const product of products) {
        const card = createElement(
            "div",
            "border border-gray-200 rounded-xl p-4 " +
            "flex flex-col sm:flex-row sm:items-center gap-4 " +
            "hover:border-emerald-300 transition"
        );

        const info = createElement("div", "flex-1 min-w-0");

        const name = createElement(
            "h3",
            "font-bold text-[#002b23] text-lg break-words",
            product.name
        );

        const category = createElement(
            "p",
            "text-sm text-gray-500 mt-1",
            `#${product.id} • ${product.category}`
        );

        const price = createElement(
            "p",
            "text-[#087b59] font-extrabold mt-2",
            `${product.price} грн`
        );

        info.append(name, category, price);

        const actions = createElement(
            "div",
            "flex flex-wrap gap-2"
        );

        const editButton = createElement(
            "button",
            "bg-[#002b23] text-white px-4 py-2 rounded-lg hover:bg-[#075443] transition",
            "Редагувати"
        );

        editButton.type = "button";
        editButton.addEventListener("click", () => startEdit(product));

        const deleteButton = createElement(
            "button",
            "bg-red-700 text-white px-4 py-2 rounded-lg hover:bg-red-800 transition",
            "Видалити"
        );

        deleteButton.type = "button";
        deleteButton.addEventListener("click", () => deleteProduct(product));

        actions.append(editButton, deleteButton);
        card.append(info, actions);
        productsList.append(card);
    }
}

// ======================================
// ОТРИМАННЯ ТОВАРІВ — GET
// ======================================

async function loadProducts() {
    loading.classList.remove("hidden");
    refreshButton.disabled = true;

    try {
        const data = await apiRequest(API_URL);

        if (!Array.isArray(data)) {
            throw new Error(
                "API повернуло неправильний формат списку товарів."
            );
        }

        products = data;
        renderProducts();

    } catch (error) {
        showNotification(error.message, "error");

    } finally {
        loading.classList.add("hidden");
        refreshButton.disabled = false;
    }
}

// ======================================
// ВАЛІДАЦІЯ ДАНИХ
// ======================================

function getFormData() {
    const name = nameInput.value.trim();
    const category = categoryInput.value;
    const price = Number(priceInput.value);
    const image = imageInput.value.trim();
    const description = descriptionInput.value.trim();

    const allowedCategories = [
        "Вудилища",
        "Котушки",
        "Приманки",
        "Гачки",
        "Аксесуари"
    ];

    if (!name || !image || !description) {
        throw new Error("Заповніть усі обов'язкові поля.");
    }

    if (!allowedCategories.includes(category)) {
        throw new Error("Оберіть коректну категорію.");
    }

    if (
        priceInput.value.trim() === "" ||
        !Number.isSafeInteger(price) ||
        price < 0
    ) {
        throw new Error("Ціна повинна бути цілим невід'ємним числом.");
    }

    if (
        name.length > 200 ||
        image.length > 255 ||
        description.length > 3000
    ) {
        throw new Error("Перевищено допустиму довжину поля.");
    }

    return {
        name,
        category,
        price,
        image,
        description
    };
}

// ======================================
// ДОДАВАННЯ ТА ОНОВЛЕННЯ — POST / PUT
// ======================================

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    let data;

    try {
        data = getFormData();
    } catch (error) {
        showNotification(error.message, "error");
        return;
    }

    const productId = productIdInput.value;
    const isEditing = Boolean(productId);

    submitButton.disabled = true;
    submitButton.textContent = "Збереження...";

    try {
        await apiRequest(
            isEditing ? `${API_URL}/${productId}` : API_URL,
            {
                method: isEditing ? "PUT" : "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(data)
            }
        );

        resetForm();

        showNotification(
            isEditing
                ? "Товар успішно оновлено."
                : "Товар успішно додано."
        );

        await loadProducts();

    } catch (error) {
        showNotification(error.message, "error");

    } finally {
        submitButton.disabled = false;
        submitButton.textContent = productIdInput.value
            ? "Зберегти зміни"
            : "Додати товар";
    }
});

// ======================================
// КНОПКИ
// ======================================

cancelButton.addEventListener("click", resetForm);
refreshButton.addEventListener("click", loadProducts);

// ======================================
// ЗАПУСК
// ======================================

loadProducts();
