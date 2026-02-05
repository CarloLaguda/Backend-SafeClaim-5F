// 1. Importiamo i moduli necessari
const express = require('express'); // Il "motore" per gestire le richieste web
const app = express(); 
const db = require('./database'); // Il file dove hai salvato le credenziali del tuo DB (Host, User, Password)

// 2. Definiamo l'Endpoint (l'indirizzo a cui l'app si collegherà)
// :vin è una variabile. Al suo posto, l'app invierà il numero di telaio specifico dell'aut
app.get('/api/v1/auto/:vin', async (req, res) => {
    
    try {
        // 3. Recuperiamo il codice del veicolo dall'URL
        const vin = req.params.vin;

        // 4. Interroghiamo il Database
        // Usiamo un "prepared statement" (il ?) per evitare attacchi hacker (SQL Injection)
        const auto = await db.query('SELECT * FROM veicoli WHERE vin = ?', [vin]);
        
        // 5. Controllo di sicurezza: l'auto esiste?
        if (auto.length === 0) {
            // Se il database non restituisce nulla, rispondiamo con un errore 404
            return res.status(404).json({ messaggio: "Veicolo non trovato" });
        }
        
        // 6. Risposta positiva
        // Inviamo i dati dell'auto in formato JSON (perfetto per le interfacce moderne)
        res.json(auto[0]);

    } catch (error) {
        // 7. Gestione imprevisti
        // Se il database è offline o c'è un errore di sintassi, il server non crasha
        res.status(500).json({ errore: "Errore interno del server" });
    }
});