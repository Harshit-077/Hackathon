const express = require('express');
const path = require('path');
const bodyParser = require('body-parser');
const knex = require('knex');


const app = express();

let initialPath = path.join(__dirname, "public");

app.use(bodyParser.json());
app.use(express.static(initialPath));

app.get('/', (req, res) => {
    res.sendFile(path.join(initialPath, "index.html"))
})

app.get('/login', (req,res) => {
    res.sendFile(path.join(initialPath, "login.html"))
})

app.get('/login', (req,res) => {
    res.sendFile(path.join(initialPath, "login.html"))
})
app.listen(3000, (req, res) => {
    console.log('listening on port 3000......')
})