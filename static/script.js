
const API = "/api";

async function api(url, options = {}) {
    const response = await fetch(API + url, {
        ...options,
        headers: {
            ...(options.body instanceof FormData ? {} : {"Content-Type": "application/json"}),
            ...options.headers
        }
    });

    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
        window.location.href = "/login";
        throw new Error("Please login");
    }

    if (!response.ok) {
        throw new Error(data.error || "Request failed");
    }

    return data;
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

function showError(error) {
    alert(error.message || "Something went wrong");
}

let projects = [];
let tasks = [];
let documents = [];
let messages = [];
let notifications = [];

let currentTaskFilter = "All";
let currentPriorityFilter = "All";


// ---------- DASHBOARD ----------

async function loadDashboard() {
    const data = await api("/dashboard");

    document.getElementById("totalProjects").textContent = data.total_projects;
    document.getElementById("completedProjects").textContent = data.completed_projects;
    document.getElementById("pendingTasks").textContent = data.pending_tasks;
    document.getElementById("totalTasks").textContent = data.total_tasks;
}


// ---------- PROJECTS ----------

async function loadProjects() {
    projects = await api("/projects");
    renderProjects();
}

function renderProjects() {
    const list = document.getElementById("projectList");
    const search = document.getElementById("projectSearch").value.toLowerCase();

    list.innerHTML = "";

    const filtered = projects.filter(project =>
        project.name.toLowerCase().includes(search)
    );

    if (filtered.length === 0) {
        list.innerHTML = "<p>No projects found.</p>";
        return;
    }

    filtered.forEach(project => {
        const card = document.createElement("div");
        card.className = "project-card";

        const progress = project.completed ? 100 : 0;

        card.innerHTML = `
            <h3>${escapeHTML(project.name)}</h3>
            <p>${project.completed ? "Completed" : "In Progress"}</p>
            <div class="progress-container">
                <div class="progress-bar" style="width:${progress}%"></div>
            </div>
            <p>${progress}% complete</p>
            <button class="toggle-project">
                ${project.completed ? "Mark Incomplete" : "Mark Completed"}
            </button>
            <button class="delete-project danger">Delete</button>
        `;

        card.querySelector(".toggle-project").addEventListener("click", async () => {
            try {
                await api(`/projects/${project.id}`, {method: "PATCH"});
                await refreshAll();
            } catch (e) { showError(e); }
        });

        card.querySelector(".delete-project").addEventListener("click", async () => {
            if (!confirm("Delete this project?")) return;
            try {
                await api(`/projects/${project.id}`, {method: "DELETE"});
                await refreshAll();
            } catch (e) { showError(e); }
        });

        list.appendChild(card);
    });
}

async function addProject(event) {
    event.preventDefault();

    const input = document.getElementById("projectName");
    const name = input.value.trim();

    if (!name) return;

    try {
        await api("/projects", {
            method: "POST",
            body: JSON.stringify({name})
        });

        input.value = "";
        await refreshAll();
    } catch (e) { showError(e); }
}


// ---------- TASKS ----------

async function loadTasks() {
    tasks = await api("/tasks");
    renderTasks();
}

function renderTasks() {
    const list = document.getElementById("taskList");
    list.innerHTML = "";

    const filtered = tasks.filter(task => {
        const statusMatch =
            currentTaskFilter === "All" ||
            (currentTaskFilter === "Pending" && !task.completed) ||
            (currentTaskFilter === "Completed" && task.completed);

        const priorityMatch =
            currentPriorityFilter === "All" ||
            task.priority === currentPriorityFilter;

        return statusMatch && priorityMatch;
    });

    if (filtered.length === 0) {
        list.innerHTML = "<p>No tasks match your filter.</p>";
        return;
    }

    filtered.forEach(task => {
        const card = document.createElement("div");
        card.className = "task-card";

        card.innerHTML = `
            <h3 class="${task.completed ? "completed" : ""}">
                ${escapeHTML(task.name)}
            </h3>
            <p class="priority ${escapeHTML(task.priority)}">
                Priority: ${escapeHTML(task.priority)}
            </p>
            <p>Deadline: ${escapeHTML(task.due_date || "Not set")}</p>
            <p>Status: ${task.completed ? "Completed" : "Pending"}</p>
            <button class="toggle-task">
                ${task.completed ? "Mark Pending" : "Complete"}
            </button>
            <button class="delete-task danger">Delete</button>
        `;

        card.querySelector(".toggle-task").addEventListener("click", async () => {
            try {
                await api(`/tasks/${task.id}`, {method: "PATCH"});
                await refreshAll();
            } catch (e) { showError(e); }
        });

        card.querySelector(".delete-task").addEventListener("click", async () => {
            if (!confirm("Delete this task?")) return;
            try {
                await api(`/tasks/${task.id}`, {method: "DELETE"});
                await refreshAll();
            } catch (e) { showError(e); }
        });

        list.appendChild(card);
    });
}

async function addTask(event) {
    event.preventDefault();

    const name = document.getElementById("taskName").value.trim();
    const priority = document.getElementById("taskPriority").value;
    const due_date = document.getElementById("taskDate").value;

    if (!name) return;

    try {
        await api("/tasks", {
            method: "POST",
            body: JSON.stringify({name, priority, due_date})
        });

        document.getElementById("taskName").value = "";
        document.getElementById("taskDate").value = "";

        await refreshAll();
    } catch (e) { showError(e); }
}


// ---------- DOCUMENTS ----------

async function loadDocuments() {
    documents = await api("/documents");
    renderDocuments();
}

function renderDocuments() {
    const list = document.getElementById("documentList");
    list.innerHTML = "";

    if (!documents.length) {
        list.innerHTML = "<p>No documents uploaded yet.</p>";
        return;
    }

    documents.forEach(doc => {
        const card = document.createElement("div");
        card.className = "document-item";

        card.innerHTML = `
            <p>📄 ${escapeHTML(doc.original_name)}</p>
            <button class="delete-document danger">Delete</button>
        `;

        card.querySelector(".delete-document").addEventListener("click", async () => {
            if (!confirm("Delete this document?")) return;
            try {
                await api(`/documents/${doc.id}`, {method: "DELETE"});
                await loadDocuments();
            } catch (e) { showError(e); }
        });

        list.appendChild(card);
    });
}

async function uploadDocument(event) {
    event.preventDefault();

    const input = document.getElementById("fileInput");
    if (!input.files.length) return;

    const formData = new FormData();
    formData.append("file", input.files[0]);

    try {
        await api("/documents", {
            method: "POST",
            body: formData
        });

        input.value = "";
        await refreshAll();
        alert("File uploaded successfully!");
    } catch (e) { showError(e); }
}


// ---------- MESSAGES ----------

async function loadMessages() {
    messages = await api("/messages");
    renderMessages();
}

function renderMessages() {
    const list = document.getElementById("messageList");
    list.innerHTML = "";

    if (!messages.length) {
        list.innerHTML = "<p>No messages yet.</p>";
        return;
    }

    messages.forEach(message => {
        const card = document.createElement("div");
        card.className = "message-item";

        card.innerHTML = `
            <p>${escapeHTML(message.message)}</p>
            <small>${escapeHTML(message.created_at)}</small>
            <button class="delete-message danger">Delete</button>
        `;

        card.querySelector(".delete-message").addEventListener("click", async () => {
            try {
                await api(`/messages/${message.id}`, {method: "DELETE"});
                await loadMessages();
            } catch (e) { showError(e); }
        });

        list.appendChild(card);
    });
}

async function addMessage(event) {
    event.preventDefault();

    const input = document.getElementById("messageInput");
    const message = input.value.trim();

    if (!message) return;

    try {
        await api("/messages", {
            method: "POST",
            body: JSON.stringify({message})
        });

        input.value = "";
        await loadMessages();
    } catch (e) { showError(e); }
}


// ---------- NOTIFICATIONS ----------

async function loadNotifications() {
    notifications = await api("/notifications");
    renderNotifications();
}

function renderNotifications() {
    const list = document.getElementById("notificationList");
    const count = document.getElementById("notificationCount");

    list.innerHTML = "";
    count.textContent = notifications.length;

    if (!notifications.length) {
        list.innerHTML = "<p>No notifications.</p>";
        return;
    }

    notifications.forEach(notification => {
        const item = document.createElement("div");
        item.className = "notification-item";

        item.innerHTML = `
            <p>${escapeHTML(notification.message)}</p>
            <small>${escapeHTML(notification.created_at)}</small>
        `;

        list.appendChild(item);
    });
}

async function clearNotifications() {
    try {
        await api("/notifications", {method: "DELETE"});
        await loadNotifications();
    } catch (e) { showError(e); }
}


// ---------- PROFILE ----------

async function loadProfile() {
    const user = await api("/me");

    document.getElementById("profileName").value = user.name;
    document.getElementById("profileEmail").value = user.email;
    document.getElementById("welcomeName").textContent = user.name;
}

async function updateProfile(event) {
    event.preventDefault();

    const name = document.getElementById("profileName").value.trim();
    const email = document.getElementById("profileEmail").value.trim();

    try {
        await api("/me", {
            method: "PUT",
            body: JSON.stringify({name, email})
        });

        await loadProfile();
        alert("Profile updated!");
    } catch (e) { showError(e); }
}


// ---------- DARK MODE ----------

function setupDarkMode() {
    const checkbox = document.getElementById("darkMode");

    checkbox.checked = localStorage.getItem("darkMode") === "true";

    document.body.classList.toggle("dark-mode", checkbox.checked);

    checkbox.addEventListener("change", () => {
        document.body.classList.toggle("dark-mode", checkbox.checked);
        localStorage.setItem("darkMode", checkbox.checked);
    });
}


// ---------- LOGOUT ----------

async function logout() {
    try {
        await api("/logout", {method: "POST"});
        window.location.href = "/login";
    } catch (e) { showError(e); }
}


// ---------- DATE & SIDEBAR ----------

function setupDate() {
    document.getElementById("currentDate").textContent =
        new Date().toLocaleDateString("en-IN", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric"
        });
}

function setupSidebar() {
    const toggle = document.getElementById("menuToggle");
    const sidebar = document.getElementById("sidebar");

    toggle.addEventListener("click", () => {
        sidebar.classList.toggle("show");
    });

    sidebar.querySelectorAll("a").forEach(link => {
        link.addEventListener("click", () => {
            if (window.innerWidth <= 760) {
                sidebar.classList.remove("show");
            }
        });
    });
}


// ---------- FILTER CONTROLS ----------

function setupFilters() {
    document.querySelectorAll(".filter-btn").forEach(button => {
        button.addEventListener("click", () => {
            currentTaskFilter = button.dataset.filter;

            document.querySelectorAll(".filter-btn").forEach(btn =>
                btn.classList.remove("active")
            );

            button.classList.add("active");
            renderTasks();
        });
    });

    document.getElementById("priorityFilter").addEventListener("change", event => {
        currentPriorityFilter = event.target.value;
        renderTasks();
    });

    document.getElementById("projectSearch").addEventListener("input", renderProjects);
}


// ---------- REFRESH ----------

async function refreshAll() {
    await Promise.all([
        loadDashboard(),
        loadProjects(),
        loadTasks(),
        loadDocuments(),
        loadMessages(),
        loadNotifications()
    ]);
}


// ---------- INITIALIZATION ----------

document.addEventListener("DOMContentLoaded", async () => {
    setupDate();
    setupDarkMode();
    setupSidebar();
    setupFilters();

    document.getElementById("projectForm").addEventListener("submit", addProject);
    document.getElementById("taskForm").addEventListener("submit", addTask);
    document.getElementById("uploadForm").addEventListener("submit", uploadDocument);
    document.getElementById("messageForm").addEventListener("submit", addMessage);
    document.getElementById("profileForm").addEventListener("submit", updateProfile);
    document.getElementById("logoutButton").addEventListener("click", logout);
    document.getElementById("clearNotifications").addEventListener("click", clearNotifications);

    try {
        await refreshAll();
        await loadProfile();
    } catch (error) {
        showError(error);
    }
});
