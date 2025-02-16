async function fetchTasks() {
    let response = await fetch('/tasks');
    let tasks = await response.json();
    let table = document.getElementById('taskTable');
    table.innerHTML = '';

    tasks.forEach(task => {
        let row = table.insertRow();
        row.innerHTML = `
            <td>${task.name}</td>
            <td>${task.category}</td>
            <td>${task.status}</td>
            <td>
                <button onclick="completeTask(${task.id})">Complete</button>
                <button onclick="deleteTask(${task.id})">Delete</button>
            </td>
        `;
    });
}

async function addTask() {
    let name = document.getElementById('taskName').value;
    let category = document.getElementById('taskCategory').value;

    await fetch('/tasks', {
        method: 'POST',
        body: new URLSearchParams({ name, category }),
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });

    fetchTasks();
}

fetchTasks();
