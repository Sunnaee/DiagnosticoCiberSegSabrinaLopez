const express = require('express');
const bodyParser = require('body-parser');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');

const app = express();
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

const fs = require('fs');
const DATA_DIR = path.join(__dirname, 'data');
const DATA_FILE = path.join(DATA_DIR, 'counts.json');

let counts = {};
let total = 0;

try {
  if (fs.existsSync(DATA_FILE)) {
    const raw = fs.readFileSync(DATA_FILE, 'utf8');
    const obj = JSON.parse(raw);
    counts = obj.counts || {};
    total = obj.total || Object.values(counts).reduce((a,b)=>a+b,0);
  }
} catch (e) { console.error('load error', e); }

function persist() {
  try {
    if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
    fs.writeFileSync(DATA_FILE, JSON.stringify({ counts, total }), 'utf8');
  } catch (e) { console.error('persist error', e); }
}

app.post('/events', (req, res) => {
  const w = (req.body && req.body.word) ? req.body.word.toLowerCase() : null;
  if (w) {
    counts[w] = (counts[w] || 0) + 1;
    total += 1;
    persist();
    broadcast({type:'update', word:w, count:counts[w]});
  }
  res.status(204).end();
});

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

function broadcast(msg) {
  const str = JSON.stringify(msg);
  wss.clients.forEach(c => { if (c.readyState === WebSocket.OPEN) c.send(str); });
}

app.get('/top/:n', (req, res) => {
  const n = parseInt(req.params.n||'10',10);
  const top = Object.entries(counts).sort((a,b)=>b[1]-a[1]).slice(0,n).map(([word,count])=>({word,count}));
  res.json({total, top});
});

wss.on('connection', ws => {
  ws.send(JSON.stringify({type:'snapshot', total, counts}));
});

const PORT = process.env.PORT || 4000;
server.listen(PORT, ()=>console.log('visualizer listening', PORT));