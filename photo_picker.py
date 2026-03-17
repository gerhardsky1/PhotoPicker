#!/usr/bin/env python3
"""
Photo Picker – Fotos aus einem Ordner auswählen, den Rest löschen.

Nutzung:
    python photo_picker.py "C:/Pfad/zum/Ordner"
    python photo_picker.py                        (öffnet Ordner-Dialog)

Öffnet eine Web-Oberfläche im Browser.
Klicke auf Fotos um sie zu BEHALTEN (grüner Rahmen).
Nicht markierte Fotos werden beim Klick auf "Nicht markierte löschen" gelöscht.
"""

import http.server
import json
import os
import platform
import secrets
import shutil
import subprocess
import sys
import socket
import threading
import urllib.parse
import webbrowser
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".heic"}


def send_to_recycle_bin(filepath):
    """Verschiebt eine Datei in den Papierkorb (Windows/Mac). Gibt True bei Erfolg zurück."""
    filepath = str(filepath)

    if IS_WINDOWS:
        import ctypes
        from ctypes import wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", ctypes.c_uint),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", ctypes.c_ushort),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", wintypes.LPCWSTR),
            ]

        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x0040
        FOF_NOCONFIRMATION = 0x0010
        FOF_SILENT = 0x0004

        fileop = SHFILEOPSTRUCTW()
        fileop.hwnd = None
        fileop.wFunc = FO_DELETE
        fileop.pFrom = filepath + '\0'
        fileop.pTo = None
        fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
        fileop.fAnyOperationsAborted = False
        fileop.hNameMappings = None
        fileop.lpszProgressTitle = None

        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
        return result == 0

    elif IS_MAC:
        try:
            # macOS: AppleScript um Datei in den Papierkorb zu verschieben
            escaped = filepath.replace('\\', '\\\\').replace('"', '\\"')
            script = f'tell application "Finder" to delete POSIX file "{escaped}"'
            subprocess.run(["osascript", "-e", script],
                           capture_output=True, timeout=10)
            return True
        except Exception:
            return False

    else:
        # Linux Fallback: endgültig löschen
        try:
            os.remove(filepath)
            return True
        except Exception:
            return False

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Photo Picker</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #1a1a2e; color: #eee;
  }
  header {
    position: sticky; top: 0; z-index: 100;
    background: #16213e; padding: 6px 12px;
    display: flex; align-items: center; gap: 6px;
    flex-wrap: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,.4);
    overflow-x: auto;
  }
  header h1 { font-size: 1rem; font-weight: 600; white-space: nowrap; }
  .stats { font-size: 0.8rem; opacity: 0.8; white-space: nowrap; }
  .sep { width: 1px; height: 24px; background: rgba(255,255,255,.15); flex-shrink: 0; }
  .btn {
    padding: 5px 10px; border: none; border-radius: 5px;
    font-size: 0.8rem; cursor: pointer; font-weight: 500;
    transition: transform .1s; display: inline-flex;
    align-items: center; gap: 4px; white-space: nowrap; flex-shrink: 0;
  }
  .btn:active { transform: scale(0.96); }
  .btn-select  { background: #0f3460; color: #fff; }
  .btn-select:hover { background: #1a4a7a; }
  .btn-keep-action { background: #00796b; color: #fff; }
  .btn-keep-action:hover { background: #00897b; }
  .btn-keep-action:disabled { background: #555; cursor: not-allowed; opacity: 0.6; }
  .btn-del   { background: #b00020; color: #fff; }
  .btn-del:hover { background: #d32f2f; }
  .btn-del:disabled { background: #555; cursor: not-allowed; opacity: 0.6; }
  .btn-del-marked { background: #e65100; color: #fff; }
  .btn-del-marked:hover { background: #ff6d00; }
  .btn-del-marked:disabled { background: #555; cursor: not-allowed; opacity: 0.6; }
  .btn-move  { background: #1b5e20; color: #fff; }
  .btn-move:hover { background: #2e7d32; }
  .btn-move:disabled { background: #555; cursor: not-allowed; opacity: 0.6; }
  .btn-copy  { background: #0d47a1; color: #fff; }
  .btn-copy:hover { background: #1565c0; }
  .btn-copy:disabled { background: #555; cursor: not-allowed; opacity: 0.6; }
  .btn-share { background: #6a1b9a; color: #fff; }
  .btn-share:hover { background: #8e24aa; }
  .btn-share:disabled { background: #555; cursor: not-allowed; opacity: 0.6; }
  .btn-lr { background: #31a8dc; color: #fff; font-weight: 700; }
  .btn-lr:hover { background: #4fc3f7; }
  .btn-lr:disabled { background: #555; cursor: not-allowed; opacity: 0.6; }
  .spacer { margin-left: auto; }
  .btn-quit { background: #444; color: #fff; padding: 5px 8px; font-size: 1rem; line-height: 1; }
  .btn-quit:hover { background: #666; }
  .folder-section { margin-bottom: 10px; }
  .folder-section-label {
    font-size: 0.72rem; opacity: 0.5; text-transform: uppercase;
    letter-spacing: 0.5px; margin-bottom: 4px;
  }
  .folder-chips { display: flex; flex-wrap: wrap; gap: 5px; }
  .folder-chip {
    padding: 5px 10px; border-radius: 4px; font-size: 0.8rem;
    border: none; cursor: pointer; text-align: left;
    max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .folder-chip.fav { background: #4a148c; color: #ddd; }
  .folder-chip.fav:hover { background: #6a1b9a; color: #fff; }
  .folder-chip.recent { background: #0f3460; color: #ccc; }
  .folder-chip.recent:hover { background: #1a4a7a; color: #fff; }
  .folder-chip-icon { margin-right: 3px; }
  .btn-gear { background: none; border: none; color: #aaa; cursor: pointer; font-size: 1rem; padding: 2px 6px; }
  .btn-gear:hover { color: #fff; }
  .fav-list { margin: 12px 0; text-align: left; }
  .fav-item {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 8px; background: #2a2a3e; border-radius: 4px;
    margin-bottom: 4px; font-size: 0.85rem;
  }
  .fav-item span { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .fav-remove { background: none; border: none; color: #f44336; cursor: pointer; font-size: 1rem; padding: 0 4px; }
  .fav-remove:hover { color: #ff6659; }

  .grid {
    display: flex; flex-wrap: wrap;
    gap: 6px; padding: 12px;
  }
  .card {
    position: relative; cursor: pointer;
    border-radius: 6px; overflow: hidden;
    border: 3px solid transparent;
    transition: border-color .15s, opacity .15s;
    background: #222; height: 227px; flex-shrink: 0;
  }
  .card img {
    height: 100%; width: auto; display: block;
    user-select: none; -webkit-user-drag: none;
  }
  .card.kept { border-color: #00c853; }
  .badge {
    position: absolute; top: 6px; right: 6px;
    width: 28px; height: 28px; border-radius: 50%;
    background: rgba(0,0,0,.55); display: flex;
    align-items: center; justify-content: center;
    font-size: 16px; pointer-events: none;
  }
  .card.kept .badge { background: #00c853; }
  .card .name {
    position: absolute; bottom: 0; left: 0; right: 0;
    background: rgba(0,0,0,.65); padding: 4px 6px;
    font-size: 0.7rem; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
  }

  .overlay {
    display: none; position: fixed; inset: 0; z-index: 200;
    background: rgba(0,0,0,.85); align-items: center;
    justify-content: center; flex-direction: column;
  }
  .overlay.active { display: flex; }
  .overlay img {
    max-width: 90vw; max-height: 80vh; object-fit: contain;
    border-radius: 8px;
  }
  .overlay .nav-btn {
    position: absolute; top: 50%; transform: translateY(-50%);
    background: rgba(255,255,255,.15); border: none; color: #fff;
    font-size: 2rem; padding: 12px 18px; cursor: pointer;
    border-radius: 8px;
  }
  .overlay .nav-btn:hover { background: rgba(255,255,255,.3); }
  .overlay .nav-btn.prev { left: 16px; }
  .overlay .nav-btn.next { right: 16px; }
  .overlay .info {
    margin-top: 12px; font-size: .9rem; display: flex;
    gap: 12px; align-items: center;
  }
  .overlay .close-btn {
    position: absolute; top: 16px; right: 16px;
    background: none; border: none; color: #fff;
    font-size: 2rem; cursor: pointer;
  }

  .confirm-overlay {
    display: none; position: fixed; inset: 0; z-index: 300;
    background: rgba(0,0,0,.8); align-items: center;
    justify-content: center;
  }
  .confirm-overlay.active { display: flex; }
  .confirm-box {
    background: #1e1e2f; padding: 32px; border-radius: 12px;
    text-align: center; max-width: 440px;
  }
  .confirm-box h2 { margin-bottom: 12px; }
  .confirm-box p { margin-bottom: 24px; opacity: .8; }
  .confirm-box .btn { margin: 0 8px; }
  .confirm-box input[type="text"] {
    width: 100%; padding: 10px; border-radius: 6px;
    border: 1px solid #555; background: #2a2a3e; color: #eee;
    font-size: 0.95rem; margin-bottom: 16px;
  }
</style>
</head>
<body>

<header>
  <h1>📷 Photo Picker</h1>
  <span class="stats" id="stats"></span>
  <div class="sep"></div>
  <button class="btn btn-select" onclick="selectAll()">☑ Alle</button>
  <button class="btn btn-select" onclick="selectNone()">☐ Keine</button>
  <div class="sep"></div>
  <button class="btn btn-keep-action" id="delBtn" onclick="confirmDeleteUnmarked()">✅ Behalten</button>
  <button class="btn btn-del-marked" id="delMarkedBtn" onclick="confirmDeleteMarked()">🗑 Löschen</button>
  <div class="sep"></div>
  <button class="btn btn-move" id="moveBtn" onclick="confirmMove()">📁 Verschieben</button>
  <button class="btn btn-copy" id="copyBtn" onclick="confirmCopy()">📋 Kopieren</button>
  <button class="btn btn-share" id="shareBtn" onclick="shareFiles()">📤 Teilen</button>
  <button class="btn btn-lr" id="lrBtn" onclick="openLightroom()">Lr</button>
  <span class="spacer"></span>
  <button class="btn btn-quit" onclick="quitApp()" title="Beenden">✕</button>
</header>

<div class="grid" id="grid"></div>

<!-- Fullscreen-Ansicht -->
<div class="overlay" id="overlay">
  <button class="close-btn" onclick="closeOverlay()">✕</button>
  <button class="nav-btn prev" onclick="navigate(-1)">‹</button>
  <button class="nav-btn next" onclick="navigate(1)">›</button>
  <img id="bigImg" src="">
  <div class="info">
    <span id="bigName"></span>
    <button class="btn btn-select" id="bigToggle" onclick="toggleCurrent()"></button>
  </div>
</div>

<!-- Bestätigung: Markierte behalten (Rest löschen) -->
<div class="confirm-overlay" id="confirmOverlay">
  <div class="confirm-box">
    <h2>✅ Markierte behalten?</h2>
    <p id="confirmText"></p>
    <p style="font-size:0.8rem; color:#ffe082; margin-bottom:16px;">♻ Alle NICHT markierten Fotos werden in den Papierkorb verschoben.</p>
    <button class="btn btn-select" onclick="closeConfirm()">Abbrechen</button>
    <button class="btn btn-keep-action" onclick="doDeleteUnmarked()">Ja, Rest in Papierkorb</button>
  </div>
</div>

<!-- Lösch-Bestätigung: Markierte -->
<div class="confirm-overlay" id="confirmMarkedOverlay">
  <div class="confirm-box">
    <h2>🗑 Markierte Fotos löschen?</h2>
    <p id="confirmMarkedText"></p>
    <p style="font-size:0.8rem; color:#ffe082; margin-bottom:16px;">♻ Die markierten Fotos werden in den Papierkorb verschoben.</p>
    <button class="btn btn-select" onclick="closeConfirmMarked()">Abbrechen</button>
    <button class="btn btn-del-marked" onclick="doDeleteMarked()">In Papierkorb</button>
  </div>
</div>

<!-- Verschieben-Dialog -->
<div class="confirm-overlay" id="moveOverlay">
  <div class="confirm-box">
    <h2 style="display:flex;align-items:center;gap:8px;">Markierte Fotos verschieben <button class="btn-gear" onclick="openFavSettings()" title="Favoriten verwalten">⚙</button></h2>
    <p id="moveText"></p>
    <div id="folderSuggestions"></div>
    <div style="display:flex; gap:8px; margin-bottom:16px;">
      <input type="text" id="moveDest" placeholder="Zielordner, z.B. C:\Bilder\Auswahl" style="margin-bottom:0;">
      <button class="btn btn-select" onclick="browseFolder()" style="white-space:nowrap;">Durchsuchen...</button>
    </div>
    <button class="btn btn-select" onclick="closeMove()">Abbrechen</button>
    <button class="btn btn-move" onclick="doMove()">Verschieben</button>
  </div>
</div>

<!-- Kopieren-Dialog -->
<div class="confirm-overlay" id="copyOverlay">
  <div class="confirm-box">
    <h2 style="display:flex;align-items:center;gap:8px;">Markierte Fotos kopieren <button class="btn-gear" onclick="openFavSettings()" title="Favoriten verwalten">⚙</button></h2>
    <p id="copyText"></p>
    <div id="copyFolderSuggestions"></div>
    <div style="display:flex; gap:8px; margin-bottom:16px;">
      <input type="text" id="copyDest" placeholder="Zielordner, z.B. C:\Bilder\Auswahl" style="margin-bottom:0;">
      <button class="btn btn-select" onclick="browseCopyFolder()" style="white-space:nowrap;">Durchsuchen...</button>
    </div>
    <button class="btn btn-select" onclick="closeCopy()">Abbrechen</button>
    <button class="btn btn-copy" onclick="doCopy()">Kopieren</button>
  </div>
</div>

<!-- Favoriten-Einstellungen -->
<div class="confirm-overlay" id="favOverlay">
  <div class="confirm-box" style="max-width:520px;">
    <h2>★ Favoriten-Ordner verwalten</h2>
    <p style="opacity:0.7;margin-bottom:12px;">Ordner die immer im Verschieben-Dialog angezeigt werden.</p>
    <div id="favList" class="fav-list"></div>
    <div style="display:flex; gap:8px; margin-bottom:16px;">
      <input type="text" id="favInput" placeholder="Ordnerpfad eingeben oder durchsuchen" style="margin-bottom:0;">
      <button class="btn btn-select" onclick="browseFavFolder()" style="white-space:nowrap;">Durchsuchen...</button>
    </div>
    <div style="display:flex; gap:8px; justify-content:space-between;">
      <button class="btn btn-move" onclick="addFavorite()">+ Hinzufügen</button>
      <button class="btn btn-select" onclick="closeFavSettings()">Fertig</button>
    </div>
  </div>
</div>

<script>
const AUTH_TOKEN = '__AUTH_TOKEN__';
const AUTH_HEADERS = {'Content-Type': 'application/json', 'X-Auth-Token': AUTH_TOKEN};
let images = [];
let kept = new Set();
let currentIdx = -1;

async function load() {
  const res = await fetch('/api/images');
  images = await res.json();
  kept = new Set();
  buildGrid();
}

function buildGrid() {
  const grid = document.getElementById('grid');
  grid.innerHTML = images.map((img, idx) => `
    <div class="card" data-name="${esc(img.name)}" data-idx="${idx}"
         ondblclick="event.stopPropagation(); openOverlay(${idx})">
      <img src="/photo/${encodeURIComponent(img.name)}" loading="lazy"
           alt="${esc(img.name)}">
      <div class="badge"></div>
      <div class="name">${esc(img.name)}</div>
    </div>
  `).join('');
  // Click-Handler auf Grid (Event Delegation)
  grid.onmousedown = function(e) {
    const card = e.target.closest('.card');
    if (!card || e.detail > 1) return; // Doppelklick ignorieren
    toggle(card.dataset.name);
  };
  updateCards();
}

function updateCards() {
  document.querySelectorAll('.card').forEach(card => {
    const name = card.dataset.name;
    const isKept = kept.has(name);
    card.classList.toggle('kept', isKept);
    card.querySelector('.badge').textContent = isKept ? '✓' : '✕';
  });
  updateStats();
}

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
          .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function toggle(name) {
  if (kept.has(name)) kept.delete(name); else kept.add(name);
  updateCards();
}

function selectAll()  { images.forEach(i => kept.add(i.name)); updateCards(); }
function selectNone() { kept.clear(); updateCards(); }

function updateStats() {
  const total = images.length;
  const k = kept.size;
  const d = total - k;
  document.getElementById('stats').textContent =
    `${total} Fotos | ✅ ${k} markiert | ◻ ${d} nicht markiert`;
  document.getElementById('delBtn').disabled = d === 0;
  document.getElementById('delMarkedBtn').disabled = k === 0;
  document.getElementById('moveBtn').disabled = k === 0;
  document.getElementById('copyBtn').disabled = k === 0;
  document.getElementById('shareBtn').disabled = k === 0;
  document.getElementById('lrBtn').disabled = k === 0;
}

/* Fullscreen */
function openOverlay(idx) {
  currentIdx = idx;
  showBig();
  document.getElementById('overlay').classList.add('active');
}
function closeOverlay() {
  document.getElementById('overlay').classList.remove('active');
}
function showBig() {
  const img = images[currentIdx];
  document.getElementById('bigImg').src = '/photo/' + encodeURIComponent(img.name);
  document.getElementById('bigName').textContent = img.name;
  document.getElementById('bigToggle').textContent =
    kept.has(img.name) ? 'Behalten ✓' : 'Nicht behalten ✕';
  document.getElementById('bigToggle').className =
    'btn ' + (kept.has(img.name) ? 'btn-select' : 'btn-del');
}
function navigate(dir) {
  currentIdx = (currentIdx + dir + images.length) % images.length;
  showBig();
}
function toggleCurrent() {
  toggle(images[currentIdx].name);
  showBig();
}

/* Markierte behalten (Rest löschen) */
function confirmDeleteUnmarked() {
  const toDelete = images.filter(i => !kept.has(i.name));
  if (toDelete.length === 0) return;
  document.getElementById('confirmText').textContent =
    `${kept.size} Foto(s) werden behalten, ${toDelete.length} Foto(s) werden gelöscht.`;
  document.getElementById('confirmOverlay').classList.add('active');
}
function closeConfirm() {
  document.getElementById('confirmOverlay').classList.remove('active');
}
async function doDeleteUnmarked() {
  const toDelete = images.filter(i => !kept.has(i.name)).map(i => i.name);
  closeConfirm();
  const res = await fetch('/api/delete', {
    method: 'POST',
    headers: AUTH_HEADERS,
    body: JSON.stringify({files: toDelete})
  });
  const result = await res.json();
  alert(`${result.deleted} nicht markierte Foto(s) in den Papierkorb verschoben.`);
  load();
}

/* Markierte löschen */
function confirmDeleteMarked() {
  const toDelete = images.filter(i => kept.has(i.name));
  if (toDelete.length === 0) return;
  document.getElementById('confirmMarkedText').textContent =
    `${toDelete.length} MARKIERTE Foto(s) werden unwiderruflich gelöscht.`;
  document.getElementById('confirmMarkedOverlay').classList.add('active');
}
function closeConfirmMarked() {
  document.getElementById('confirmMarkedOverlay').classList.remove('active');
}
async function doDeleteMarked() {
  const toDelete = images.filter(i => kept.has(i.name)).map(i => i.name);
  closeConfirmMarked();
  const res = await fetch('/api/delete', {
    method: 'POST',
    headers: AUTH_HEADERS,
    body: JSON.stringify({files: toDelete})
  });
  const result = await res.json();
  alert(`${result.deleted} markierte Foto(s) in den Papierkorb verschoben.`);
  kept.clear();
  load();
}

/* Ordner-Verwaltung (localStorage) */
function getRecentFolders() {
  try { return JSON.parse(localStorage.getItem('pp_recent_folders') || '[]'); }
  catch(e) { return []; }
}
function addRecentFolder(folder) {
  let recent = getRecentFolders().filter(f => f !== folder);
  recent.unshift(folder);
  if (recent.length > 5) recent = recent.slice(0, 5);
  localStorage.setItem('pp_recent_folders', JSON.stringify(recent));
}
function getFavFolders() {
  try { return JSON.parse(localStorage.getItem('pp_favorite_folders') || '[]'); }
  catch(e) { return []; }
}
function saveFavFolders(favs) {
  localStorage.setItem('pp_favorite_folders', JSON.stringify(favs));
}
function folderName(f) {
  const parts = f.replace(/\\/g, '/').split('/').filter(Boolean);
  return parts.pop() || f;
}

function showFolderSuggestions(containerId, inputId) {
  containerId = containerId || 'folderSuggestions';
  inputId = inputId || 'moveDest';
  const container = document.getElementById(containerId);
  const favs = getFavFolders();
  const recent = getRecentFolders();
  let html = '';

  if (favs.length > 0) {
    html += '<div class="folder-section"><div class="folder-section-label">Favoriten</div><div class="folder-chips" id="favChips">';
    favs.forEach((f, i) => {
      html += '<button class="folder-chip fav" data-path="' + esc(f) + '" title="' + esc(f) + '"><span class="folder-chip-icon">★</span>' + esc(folderName(f)) + '</button>';
    });
    html += '</div></div>';
  }

  if (recent.length > 0) {
    html += '<div class="folder-section"><div class="folder-section-label">Zuletzt verwendet</div><div class="folder-chips" id="recentChips">';
    recent.forEach((f, i) => {
      html += '<button class="folder-chip recent" data-path="' + esc(f) + '" title="' + esc(f) + '"><span class="folder-chip-icon">⏱</span>' + esc(folderName(f)) + '</button>';
    });
    html += '</div></div>';
  }

  container.innerHTML = html;

  // Event Delegation: Klick auf Chip setzt Pfad ins Textfeld
  container.onclick = function(e) {
    const chip = e.target.closest('.folder-chip');
    if (chip && chip.dataset.path) {
      document.getElementById(inputId).value = chip.dataset.path;
    }
  };
}

/* Favoriten-Einstellungen */
function openFavSettings() {
  renderFavList();
  document.getElementById('favInput').value = '';
  document.getElementById('favOverlay').classList.add('active');
}
function closeFavSettings() {
  document.getElementById('favOverlay').classList.remove('active');
  showFolderSuggestions(); // Aktualisieren
}
function renderFavList() {
  const favs = getFavFolders();
  const container = document.getElementById('favList');
  if (favs.length === 0) {
    container.innerHTML = '<p style="opacity:0.4;font-size:0.85rem;">Noch keine Favoriten gespeichert.</p>';
    return;
  }
  container.innerHTML = favs.map((f, i) =>
    '<div class="fav-item"><span title="' + esc(f) + '">' + esc(f) + '</span>' +
    '<button class="fav-remove" data-idx="' + i + '" title="Entfernen">✕</button></div>'
  ).join('');
  container.onclick = function(e) {
    const btn = e.target.closest('.fav-remove');
    if (btn) {
      const idx = parseInt(btn.dataset.idx);
      const favs = getFavFolders();
      favs.splice(idx, 1);
      saveFavFolders(favs);
      renderFavList();
    }
  };
}
function addFavorite() {
  const input = document.getElementById('favInput');
  const folder = input.value.trim();
  if (!folder) { alert('Bitte einen Ordnerpfad eingeben.'); return; }
  const favs = getFavFolders();
  if (favs.includes(folder)) { alert('Dieser Ordner ist bereits ein Favorit.'); return; }
  favs.push(folder);
  saveFavFolders(favs);
  input.value = '';
  renderFavList();
}
async function browseFavFolder() {
  const res = await fetch('/api/browse', {method: 'POST', headers: {'X-Auth-Token': AUTH_TOKEN}});
  const result = await res.json();
  if (result.folder) {
    document.getElementById('favInput').value = result.folder;
  }
}

/* Verschieben */
function confirmMove() {
  const toMove = images.filter(i => kept.has(i.name));
  if (toMove.length === 0) return;
  document.getElementById('moveText').textContent =
    `${toMove.length} Foto(s) in einen anderen Ordner verschieben:`;
  document.getElementById('moveDest').value = '';
  showFolderSuggestions();
  document.getElementById('moveOverlay').classList.add('active');
  setTimeout(() => document.getElementById('moveDest').focus(), 100);
}
function closeMove() {
  document.getElementById('moveOverlay').classList.remove('active');
}
async function browseFolder() {
  const res = await fetch('/api/browse', {method: 'POST', headers: {'X-Auth-Token': AUTH_TOKEN}});
  const result = await res.json();
  if (result.folder) {
    document.getElementById('moveDest').value = result.folder;
  }
}
async function doMove() {
  const dest = document.getElementById('moveDest').value.trim();
  if (!dest) { alert('Bitte Zielordner eingeben.'); return; }
  const toMove = images.filter(i => kept.has(i.name)).map(i => i.name);
  closeMove();
  const res = await fetch('/api/move', {
    method: 'POST',
    headers: AUTH_HEADERS,
    body: JSON.stringify({files: toMove, destination: dest})
  });
  const result = await res.json();
  if (result.error) { alert('Fehler: ' + result.error); return; }
  addRecentFolder(dest);
  alert(`${result.moved} Foto(s) verschoben nach:\n${dest}`);
  load();
}

/* Kopieren */
function confirmCopy() {
  const toCopy = images.filter(i => kept.has(i.name));
  if (toCopy.length === 0) return;
  document.getElementById('copyText').textContent =
    `${toCopy.length} Foto(s) in einen anderen Ordner kopieren:`;
  document.getElementById('copyDest').value = '';
  showFolderSuggestions('copyFolderSuggestions', 'copyDest');
  document.getElementById('copyOverlay').classList.add('active');
  setTimeout(() => document.getElementById('copyDest').focus(), 100);
}
function closeCopy() {
  document.getElementById('copyOverlay').classList.remove('active');
}
async function browseCopyFolder() {
  const res = await fetch('/api/browse', {method: 'POST', headers: {'X-Auth-Token': AUTH_TOKEN}});
  const result = await res.json();
  if (result.folder) {
    document.getElementById('copyDest').value = result.folder;
  }
}
async function doCopy() {
  const dest = document.getElementById('copyDest').value.trim();
  if (!dest) { alert('Bitte Zielordner eingeben.'); return; }
  const toCopy = images.filter(i => kept.has(i.name)).map(i => i.name);
  closeCopy();
  const res = await fetch('/api/copy', {
    method: 'POST',
    headers: AUTH_HEADERS,
    body: JSON.stringify({files: toCopy, destination: dest})
  });
  const result = await res.json();
  if (result.error) { alert('Fehler: ' + result.error); return; }
  addRecentFolder(dest);
  alert(`${result.copied} Foto(s) kopiert nach:\n${dest}`);
  kept.clear();
  updateCards();
}

/* In Lightroom öffnen */
async function openLightroom() {
  const toOpen = images.filter(i => kept.has(i.name)).map(i => i.name);
  if (toOpen.length === 0) return;
  const res = await fetch('/api/open-lightroom', {
    method: 'POST',
    headers: AUTH_HEADERS,
    body: JSON.stringify({files: toOpen})
  });
  const result = await res.json();
  if (result.error) { alert('Fehler: ' + result.error); return; }
  kept.clear();
  updateCards();
}

/* Teilen (Web Share API) */
async function shareFiles() {
  const toShare = images.filter(i => kept.has(i.name));
  if (toShare.length === 0) return;

  if (navigator.canShare) {
    try {
      const files = [];
      for (const img of toShare) {
        const res = await fetch('/photo/' + encodeURIComponent(img.name));
        const blob = await res.blob();
        const mime = blob.type || 'image/jpeg';
        files.push(new File([blob], img.name, {type: mime}));
      }
      if (navigator.canShare({files})) {
        await navigator.share({
          title: `${files.length} Foto(s)`,
          files: files
        });
        kept.clear();
        updateCards();
        return;
      }
    } catch (e) {
      if (e.name === 'AbortError') return;
    }
  }

  alert(
    `Die Teilen-Funktion wird von deinem Browser nicht unterstützt.\n\n` +
    `Alternativ:\n` +
    `1. Nutze "Kopieren" um die Fotos in einen Ordner zu kopieren\n` +
    `2. Teile sie dann manuell über die gewünschte App`
  );
}

/* Beenden */
async function quitApp() {
  if (!confirm('PhotoPicker beenden?')) return;
  try { await fetch('/api/shutdown', {method: 'POST', headers: {'X-Auth-Token': AUTH_TOKEN}}); } catch(e) {}
  document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-size:1.5rem;">PhotoPicker beendet. Du kannst diesen Tab schließen.</div>';
}

/* Shift+Hover Mehrfachauswahl */
let shiftSelecting = false;
document.getElementById('grid').addEventListener('mouseover', function(e) {
  if (!e.shiftKey) return;
  const card = e.target.closest('.card');
  if (!card) return;
  const name = card.dataset.name;
  if (!kept.has(name)) {
    kept.add(name);
    card.classList.add('kept');
    card.querySelector('.badge').textContent = '✓';
    updateStats();
  }
});

/* Tastatur-Steuerung */
document.addEventListener('keydown', e => {
  const ov = document.getElementById('overlay');
  if (ov.classList.contains('active')) {
    if (e.key === 'Escape') closeOverlay();
    if (e.key === 'ArrowLeft')  navigate(-1);
    if (e.key === 'ArrowRight') navigate(1);
    if (e.key === ' ') { e.preventDefault(); toggleCurrent(); }
  }
});

load();
</script>
</body>
</html>"""


MAX_BODY = 1024 * 1024  # 1 MB max für API-Requests


class PhotoHandler(http.server.BaseHTTPRequestHandler):
    folder = ""
    server_ref = None
    auth_token = ""

    def log_message(self, format, *args):
        pass  # leise

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/":
            page = HTML_PAGE.replace("__AUTH_TOKEN__", self.auth_token)
            self._respond(200, "text/html", page.encode())

        elif path == "/api/images":
            files = sorted(
                [
                    {"name": f.name, "size": f.stat().st_size, "mtime": f.stat().st_mtime}
                    for f in Path(self.folder).iterdir()
                    if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
                ],
                key=lambda x: x["mtime"],
                reverse=True,
            )
            self._respond(200, "application/json", json.dumps(files).encode())

        elif path.startswith("/photo/"):
            name = urllib.parse.unquote(path[7:])
            fpath = (Path(self.folder) / name).resolve()
            folder_resolved = Path(self.folder).resolve()
            if str(fpath).startswith(str(folder_resolved) + os.sep) and fpath.is_file() and fpath.suffix.lower() in IMAGE_EXTENSIONS:
                ext = fpath.suffix.lower()
                ct = {
                    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".png": "image/png", ".gif": "image/gif",
                    ".bmp": "image/bmp", ".webp": "image/webp",
                    ".tiff": "image/tiff", ".tif": "image/tiff",
                }.get(ext, "application/octet-stream")
                self._respond(200, ct, fpath.read_bytes())
            else:
                self._respond(404, "text/plain", b"Not found")
        else:
            self._respond(404, "text/plain", b"Not found")

    def do_POST(self):
        if not self._check_origin() or not self._check_auth():
            return
        path = urllib.parse.urlparse(self.path).path

        if path == "/api/delete":
            body = self._read_body()
            if body is None:
                self._respond(400, "application/json", b'{"error":"Ungueltige Anfrage"}')
                return
            deleted = 0
            for name in body.get("files", []):
                fpath = Path(self.folder) / name
                try:
                    fpath = fpath.resolve()
                    folder_resolved = Path(self.folder).resolve()
                    if fpath.parent == folder_resolved and fpath.is_file() and fpath.suffix.lower() in IMAGE_EXTENSIONS:
                        if send_to_recycle_bin(fpath):
                            deleted += 1
                except Exception:
                    pass
            self._respond(200, "application/json",
                          json.dumps({"deleted": deleted}).encode())

        elif path == "/api/browse":
            # Öffnet nativen Windows-Ordnerdialog
            folder_selected = ""
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                folder_selected = filedialog.askdirectory(
                    title="Zielordner auswählen",
                    parent=root
                )
                root.destroy()
            except Exception:
                pass
            self._respond(200, "application/json",
                          json.dumps({"folder": folder_selected}).encode())
            return

        elif path == "/api/shutdown":
            self._respond(200, "application/json", json.dumps({"ok": True}).encode())
            threading.Thread(target=self._shutdown, daemon=True).start()
            return

        elif path == "/api/move":
            body = self._read_body()
            if body is None:
                self._respond(400, "application/json", b'{"error":"Ungueltige Anfrage"}')
                return
            dest = body.get("destination", "").strip()
            if not dest:
                self._respond(200, "application/json",
                              json.dumps({"error": "Kein Zielordner angegeben"}).encode())
                return
            dest_path = Path(dest)
            try:
                dest_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self._respond(200, "application/json",
                              json.dumps({"error": "Ordner konnte nicht erstellt werden."}).encode())
                return
            moved = 0
            for name in body.get("files", []):
                fpath = Path(self.folder) / name
                try:
                    fpath = fpath.resolve()
                    folder_resolved = Path(self.folder).resolve()
                    if fpath.parent == folder_resolved and fpath.is_file() and fpath.suffix.lower() in IMAGE_EXTENSIONS:
                        shutil.move(str(fpath), str(dest_path / fpath.name))
                        moved += 1
                except Exception:
                    pass
            self._respond(200, "application/json",
                          json.dumps({"moved": moved}).encode())

        elif path == "/api/copy":
            body = self._read_body()
            if body is None:
                self._respond(400, "application/json", b'{"error":"Ungueltige Anfrage"}')
                return
            dest = body.get("destination", "").strip()
            if not dest:
                self._respond(200, "application/json",
                              json.dumps({"error": "Kein Zielordner angegeben"}).encode())
                return
            dest_path = Path(dest)
            try:
                dest_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self._respond(200, "application/json",
                              json.dumps({"error": "Ordner konnte nicht erstellt werden."}).encode())
                return
            copied = 0
            for name in body.get("files", []):
                fpath = Path(self.folder) / name
                try:
                    fpath = fpath.resolve()
                    folder_resolved = Path(self.folder).resolve()
                    if fpath.parent == folder_resolved and fpath.is_file() and fpath.suffix.lower() in IMAGE_EXTENSIONS:
                        shutil.copy2(str(fpath), str(dest_path / fpath.name))
                        copied += 1
                except Exception:
                    pass
            self._respond(200, "application/json",
                          json.dumps({"copied": copied}).encode())

        elif path == "/api/open-lightroom":
            body = self._read_body()
            if body is None:
                self._respond(400, "application/json", b'{"error":"Ungueltige Anfrage"}')
                return
            # Lightroom suchen
            lr_exe = self._find_lightroom()
            if not lr_exe:
                self._respond(200, "application/json",
                              json.dumps({"error": "Lightroom wurde nicht gefunden. Bitte installiere Adobe Lightroom Classic."}).encode())
                return
            # Dateipfade sammeln
            file_paths = []
            folder_resolved = Path(self.folder).resolve()
            for name in body.get("files", []):
                fpath = (Path(self.folder) / name).resolve()
                if str(fpath).startswith(str(folder_resolved) + os.sep) and fpath.is_file() and fpath.suffix.lower() in IMAGE_EXTENSIONS:
                    file_paths.append(str(fpath))
            if not file_paths:
                self._respond(200, "application/json",
                              json.dumps({"error": "Keine gültigen Dateien ausgewählt."}).encode())
                return
            try:
                if IS_MAC and str(lr_exe).endswith(".app"):
                    subprocess.Popen(["open", "-a", str(lr_exe), "--args"] + file_paths)
                else:
                    popen_kwargs = {}
                    if IS_WINDOWS:
                        popen_kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
                    subprocess.Popen(
                        [str(lr_exe)] + file_paths,
                        **popen_kwargs
                    )
                self._respond(200, "application/json",
                              json.dumps({"ok": True, "opened": len(file_paths)}).encode())
            except Exception:
                self._respond(200, "application/json",
                              json.dumps({"error": "Lightroom konnte nicht gestartet werden."}).encode())

        else:
            self._respond(404, "text/plain", b"Not found")

    def _find_lightroom(self):
        """Sucht Adobe Lightroom Classic auf dem System (Windows + Mac)."""
        if IS_MAC:
            # macOS: Lightroom liegt in /Applications
            candidates = [
                Path("/Applications/Adobe Lightroom Classic/Adobe Lightroom Classic.app"),
                Path("/Applications/Adobe Lightroom Classic.app"),
            ]
            for app in candidates:
                if app.exists():
                    return app
            # Suche in /Applications nach Lightroom
            apps_dir = Path("/Applications")
            if apps_dir.is_dir():
                for item in apps_dir.iterdir():
                    if "lightroom" in item.name.lower() and item.suffix == ".app":
                        return item
            return None

        # Windows
        search_dirs = [
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")),
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")),
        ]
        for base in search_dirs:
            adobe_dir = base / "Adobe"
            if not adobe_dir.is_dir():
                continue
            for sub in adobe_dir.iterdir():
                if sub.is_dir() and "lightroom" in sub.name.lower():
                    exe = sub / "Lightroom.exe"
                    if exe.is_file():
                        return exe
                    exe = sub / "lightroom.exe"
                    if exe.is_file():
                        return exe
        return None

    def _shutdown(self):
        # Alle anderen PhotoPicker-Instanzen beenden
        try:
            my_pid = os.getpid()
            if IS_WINDOWS:
                subprocess.run(
                    ["powershell", "-Command",
                     f"Get-Process -Name PhotoPicker -ErrorAction SilentlyContinue | "
                     f"Where-Object {{ $_.Id -ne {my_pid} }} | Stop-Process -Force"],
                    creationflags=0x08000000,
                    timeout=5
                )
            else:
                subprocess.run(
                    ["pkill", "-f", "PhotoPicker"],
                    capture_output=True, timeout=5
                )
        except Exception:
            pass
        # Eigenen Server beenden
        if self.server_ref:
            self.server_ref.shutdown()

    def _check_origin(self):
        """Prüft ob der Request von unserem Server kommt (CORS-Schutz)."""
        origin = self.headers.get("Origin", "")
        if origin and not origin.startswith("http://127.0.0.1"):
            self._respond_raw(403, "text/plain", b"Forbidden")
            return False
        return True

    def _check_auth(self):
        """Prüft Auth-Token bei POST-Requests."""
        token = self.headers.get("X-Auth-Token", "")
        if token != self.auth_token:
            self._respond_raw(403, "text/plain", b"Forbidden")
            return False
        return True

    def _read_body(self):
        """Liest Request-Body mit Größenlimit."""
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return None
        if length > MAX_BODY:
            return None
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def _respond_raw(self, code, content_type, data):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _respond(self, code, content_type, data):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def main():
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        # Ordner-Dialog mit tkinter
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            folder = filedialog.askdirectory(title="Ordner mit Fotos auswählen")
            root.destroy()
            if not folder:
                print("Kein Ordner ausgewählt.")
                sys.exit(0)
        except ImportError:
            print("Nutzung: python photo_picker.py <ordner>")
            sys.exit(1)

    folder = os.path.abspath(folder)
    if not os.path.isdir(folder):
        print(f"Ordner nicht gefunden: {folder}")
        sys.exit(1)

    # Bilder zählen
    count = sum(
        1 for f in Path(folder).iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )
    if count == 0:
        print(f"Keine Bilder gefunden in: {folder}")
        sys.exit(1)

    port = find_free_port()
    PhotoHandler.folder = folder
    PhotoHandler.auth_token = secrets.token_hex(16)

    server = http.server.HTTPServer(("127.0.0.1", port), PhotoHandler)
    PhotoHandler.server_ref = server
    url = f"http://127.0.0.1:{port}"

    print(f"Ordner:  {folder}")
    print(f"Bilder:  {count}")
    print(f"Öffne:   {url}")
    print(f"Beenden: Strg+C")

    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
        server.server_close()


if __name__ == "__main__":
    main()
