require("dotenv").config();

const express = require("express");
const nodemailer = require("nodemailer");

const app = express();
app.use(express.json());

// ── Config ─────────────────────────────────────────────────────────────────

const PORT           = process.env.PORT           || 3001;
const GMAIL_USER     = process.env.GMAIL_USER;
const GMAIL_PASSWORD = process.env.GMAIL_APP_PASSWORD;
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET;

// Warn loudly at startup if any required env var is missing
["GMAIL_USER", "GMAIL_APP_PASSWORD", "WEBHOOK_SECRET"].forEach((key) => {
  if (!process.env[key]) {
    console.warn(`[startup] WARNING: ${key} is not set in .env`);
  }
});

// ── Nodemailer transporter ──────────────────────────────────────────────────

const transporter = nodemailer.createTransport({
  host: "smtp.gmail.com",
  port: 465,
  secure: true,           // SSL from the start (no STARTTLS)
  auth: {
    user: GMAIL_USER,
    pass: GMAIL_PASSWORD,
  },
});

// ── Middleware: request logger ──────────────────────────────────────────────

app.use((req, _res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
});

// ── Routes ──────────────────────────────────────────────────────────────────

// Health check
app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

// Download notification
app.post("/notify", async (req, res) => {
  // 1. Validate Authorization header
  const authHeader = req.headers["authorization"] || "";
  const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : null;

  if (!token || token !== WEBHOOK_SECRET) {
    console.warn("[notify] 401 — invalid or missing Authorization header");
    return res.status(401).json({ status: "unauthorized" });
  }

  // 2. Parse and validate body
  const { recipient_email, filename, downloaded_at } = req.body;

  if (!recipient_email || !filename || !downloaded_at) {
    console.warn("[notify] 400 — missing required body fields");
    return res.status(400).json({
      status: "error",
      detail: "Body must include recipient_email, filename, and downloaded_at",
    });
  }

  console.log(`[notify] Sending notification to ${recipient_email} for file "${filename}"`);

  // 3. Send email
  try {
    await transporter.sendMail({
      from: `"Secure File Drop" <${GMAIL_USER}>`,
      to: recipient_email,
      subject: "Your file was downloaded — Secure File Drop",
      text: [
        `Hi,`,
        ``,
        `Your file "${filename}" was downloaded at ${downloaded_at} UTC.`,
        ``,
        `If you did not expect this, your share link may have been forwarded.`,
        ``,
        `— Secure File Drop`,
      ].join("\n"),
    });

    console.log(`[notify] Email sent successfully to ${recipient_email}`);
    return res.json({ status: "email sent" });

  } catch (err) {
    console.error(`[notify] Failed to send email: ${err.message}`);
    return res.status(500).json({ status: "error", detail: err.message });
  }
});

// ── Start ───────────────────────────────────────────────────────────────────

app.listen(PORT, () => {
  console.log(`[startup] Webhook service running on http://localhost:${PORT}`);
  console.log(`[startup] GMAIL_USER = ${GMAIL_USER || "(not set)"}`);
});
