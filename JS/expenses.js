let expenses = [];
const ctx = document.getElementById('expense-chart').getContext('2d');

document.getElementById('add-expense').addEventListener('click', function() {
    const name = document.getElementById('expense-name').value;
    const amount = parseFloat(document.getElementById('expense-amount').value);

    if (name && amount) {
        addExpense(name, amount);
    } else {
        alert('Please fill in both fields.');
    }
});

document.getElementById('get-analysis').addEventListener('click', function() {
    updateChart();
});

function addExpense(name, amount) {
    expenses.push({ name, amount });
    // Optionally, you can store expenses in local storage
}

function updateChart() {
    const data = {
        labels: expenses.map(expense => expense.name),
        datasets: [{
            label: 'Expenses',
            data: expenses.map(expense => expense.amount),
            backgroundColor: [
                'rgba(255, 99, 132, 0.5)',
                'rgba(54, 162, 235, 0.5)',
                'rgba(255, 206, 86, 0.5)',
                'rgba(75, 192, 192, 0.5)',
                'rgba(153, 102, 255, 0.5)',
                'rgba(255, 159, 64, 0.5)'
            ],
            borderColor: [
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 192, 1)',
                'rgba(153, 102, 255, 1)',
                'rgba(255, 159, 64, 1)'
            ],
            borderWidth: 1
        }]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false
    };

    new Chart(ctx, {
        type: 'pie',
        data: data,
        options: options
    });
}