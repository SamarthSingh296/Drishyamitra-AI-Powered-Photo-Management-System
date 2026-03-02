const express = require('express');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const multer = require('multer');
const fs = require('fs');

const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Setup multer for handling form-data and retaining uploaded files temporarily
const upload = multer({ dest: 'uploads/' });

// Create a new WhatsApp client with LocalAuth to persist session across restarts
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

let isReady = false;

// Generate QR Code for authentication
client.on('qr', (qr) => {
    console.log('\n======================================================');
    console.log('   SCAN THIS QR CODE TO AUTHENTICATE WHATSAPP');
    console.log('======================================================\n');
    qrcode.generate(qr, { small: true });
});

// Client is ready and authenticated
client.on('ready', () => {
    isReady = true;
    console.log('WhatsApp Client is READY! You can now send messages and photos.');
});

client.on('authenticated', () => {
    console.log('Authentication Successful.');
});

client.on('auth_failure', () => {
    console.error('Authentication Failed. Please delete the .wwebjs_auth folder and try scanning again.');
    isReady = false;
});

client.on('disconnected', (reason) => {
    console.warn('Client was disconnected', reason);
    isReady = false;
    // Attempt to restart
    client.initialize();
});

// Endpoint to send simple text messages
app.post('/send-message', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({ success: false, error: 'WhatsApp client is not ready yet. Please authenticate.' });
    }

    const { number, message } = req.body;

    if (!number || !message) {
        return res.status(400).json({ success: false, error: 'number and message are required in the JSON body.' });
    }

    try {
        const msg = await client.sendMessage(number, message);
        return res.json({ success: true, messageId: msg.id.id });
    } catch (err) {
        console.error('Failed to send message:', err);
        return res.status(500).json({ success: false, error: err.toString() });
    }
});

// Endpoint to send media (photos)
app.post('/send-media', upload.single('file'), async (req, res) => {
    if (!isReady) {
        if (req.file) fs.unlinkSync(req.file.path); // cleanup
        return res.status(503).json({ success: false, error: 'WhatsApp client is not ready yet. Please authenticate.' });
    }

    const { number, caption } = req.body;

    if (!number || !req.file) {
        if (req.file) fs.unlinkSync(req.file.path); // cleanup
        return res.status(400).json({ success: false, error: 'number and file (multipart form data) are required.' });
    }

    try {
        // Read file from disk and convert to MessageMedia
        const media = MessageMedia.fromFilePath(req.file.path);

        // Let's preserve the original filename or mime type if needed, but fromFilePath tries to infer.
        // It's mostly reliable.

        // Send media
        const msg = await client.sendMessage(number, media, { caption: caption || '' });

        // Clean up temp file
        fs.unlinkSync(req.file.path);

        return res.json({ success: true, messageId: msg.id.id });
    } catch (err) {
        console.error('Failed to send media:', err);
        if (req.file && fs.existsSync(req.file.path)) {
            fs.unlinkSync(req.file.path);
        }
        return res.status(500).json({ success: false, error: err.toString() });
    }
});

app.get('/status', (req, res) => {
    res.json({
        success: true,
        ready: isReady,
        message: isReady ? 'WhatsApp Service is Online' : 'Waiting for Authentication/Connecting'
    });
});

// Start Express server and initialize WhatsApp WebJS
app.listen(port, () => {
    console.log(`WhatsApp API Microservice listening on port ${port}`);
    console.log('Initializing WhatsApp Client...');
    client.initialize();
});
