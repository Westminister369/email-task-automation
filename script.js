// LocalStorage keys used by the static GitHub Pages dashboard.
const STORAGE_KEYS = {
  config: 'aiEmailAutomationConfig',
  logs: 'aiEmailAutomationLogs',
};

const defaultConfig = {
  gmailFileName: '',
  openaiKey: '',
  sheetId: '',
  backendUrl: '',
};

const state = {
  config: loadConfig(),
  logs: loadLogs(),
};

const SIMULATION_STEPS = [
  'Simulation: would fetch 5 unread emails',
  'Simulation: would summarize emails successfully',
  'Simulation: would save extracted tasks to Google Sheets',
];

const gmailInput = document.querySelector('#gmailCredentials');
const openaiInput = document.querySelector('#openaiKey');
const sheetInput = document.querySelector('#sheetId');
const runButton = document.querySelector('#runAutomation');
const spinner = document.querySelector('#spinner');
const outputList = document.querySelector('#mockOutput');
const logsList = document.querySelector('#logsList');
const clearLogsButton = document.querySelector('#clearLogs');
const configStatus = document.querySelector('#configStatus');
const modeStatus = document.querySelector('#modeStatus');
const backendUrlInput = document.querySelector('#backendUrl');

// Initialize saved values and bind dashboard interactions.
document.addEventListener('DOMContentLoaded', () => {
  openaiInput.value = state.config.openaiKey;
  sheetInput.value = state.config.sheetId;
  backendUrlInput.value = state.config.backendUrl;
  renderLogs();
  renderConfigStatus();
  bindNavigationState();
});

// Save buttons persist setup data locally. Later these actions can call backend APIs.
document.querySelectorAll('[data-save]').forEach((button) => {
  button.addEventListener('click', () => {
    const section = button.dataset.save;

    if (section === 'gmail') {
      state.config.gmailFileName = gmailInput.files[0]?.name || state.config.gmailFileName;
      addLog(
        state.config.gmailFileName
          ? `Saved Gmail credentials placeholder: ${state.config.gmailFileName}`
          : 'No Gmail credentials file selected yet.'
      );
    }

    if (section === 'openai') {
      state.config.openaiKey = openaiInput.value.trim();
      addLog(
        state.config.openaiKey ? 'Saved OpenAI key locally.' : 'OpenAI key cleared.'
      );
    }

    if (section === 'sheets') {
      state.config.sheetId = sheetInput.value.trim();
      addLog(
        state.config.sheetId ? 'Saved Google Sheets ID locally.' : 'Google Sheets ID cleared.'
      );
    }

    if (section === 'backend') {
      state.config.backendUrl = normalizeBackendUrl(backendUrlInput.value);
      backendUrlInput.value = state.config.backendUrl;
      addLog(
        state.config.backendUrl
          ? `Saved backend automation URL: ${state.config.backendUrl}`
          : 'Backend URL cleared. Dashboard will run in simulation mode.'
      );
    }

    saveConfig();
    renderConfigStatus();
  });
});

// Run button simulates the future backend workflow with a spinner and mock output.
runButton.addEventListener('click', async () => {
  outputList.innerHTML = '';
  runButton.disabled = true;
  spinner.classList.remove('hidden');
  addLog('Automation run started.');

  try {
    if (state.config.backendUrl) {
      await runBackendAutomation();
    } else {
      await runSimulation();
    }
  } catch (error) {
    addOutput(`Run failed: ${error.message}`);
    addLog(`Run failed: ${error.message}`);
  } finally {
    spinner.classList.add('hidden');
    runButton.disabled = false;
  }
});

clearLogsButton.addEventListener('click', () => {
  state.logs = [];
  saveLogs();
  renderLogs();
});

function loadConfig() {
  try {
    const savedConfig = JSON.parse(localStorage.getItem(STORAGE_KEYS.config)) || {};
    return { ...defaultConfig, ...savedConfig };
  } catch (error) {
    console.warn('Failed to parse saved config.', error);
    return { ...defaultConfig };
  }
}

function saveConfig() {
  localStorage.setItem(STORAGE_KEYS.config, JSON.stringify(state.config));
}

function loadLogs() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEYS.logs)) || [];
  } catch (error) {
    console.warn('Failed to parse saved logs.', error);
    return [];
  }
}

function saveLogs() {
  localStorage.setItem(STORAGE_KEYS.logs, JSON.stringify(state.logs));
}

function addLog(message) {
  state.logs.unshift({
    message,
    timestamp: new Date().toLocaleString(),
  });
  state.logs = state.logs.slice(0, 50);
  saveLogs();
  renderLogs();
}

function renderLogs() {
  logsList.innerHTML = '';

  if (!state.logs.length) {
    const emptyState = document.createElement('div');
    emptyState.className = 'log-entry';
    emptyState.textContent = 'No logs yet. Save settings or run the automation to begin.';
    logsList.appendChild(emptyState);
    return;
  }

  state.logs.forEach((entry) => {
    const row = document.createElement('div');
    row.className = 'log-entry';
    const timestamp = document.createElement('strong');
    timestamp.textContent = entry.timestamp;

    const message = document.createElement('span');
    message.textContent = ` — ${entry.message}`;

    row.append(timestamp, message);
    logsList.appendChild(row);
  });
}

function renderConfigStatus() {
  const completed = [
    state.config.gmailFileName,
    state.config.openaiKey,
    state.config.sheetId,
  ].filter(Boolean).length;
  configStatus.textContent = `${completed}/3 setup items saved`;
  modeStatus.textContent = state.config.backendUrl
    ? 'Backend URL saved; Run Automation will call the backend.'
    : 'No backend URL saved; Run Automation is simulation only.';
}

function bindNavigationState() {
  const links = document.querySelectorAll('.nav-link');
  links.forEach((link) => {
    link.addEventListener('click', () => {
      links.forEach((item) => item.classList.remove('active'));
      link.classList.add('active');
    });
  });
}

function addOutput(message) {
  const item = document.createElement('li');
  item.textContent = message;
  outputList.appendChild(item);
}

async function runSimulation() {
  addLog('Simulation mode: no backend URL configured. No Gmail messages or Sheet rows will be changed.');
  await wait(1100);

  SIMULATION_STEPS.forEach((message, index) => {
    addOutput(message);
    addLog(`${index + 1}/3 ${message}`);
  });

  addLog('Simulation completed. Configure a backend URL to process real Gmail messages.');
}

async function runBackendAutomation() {
  addLog(`Calling backend automation API: ${state.config.backendUrl}`);

  // Backend integration point: the backend should own Gmail OAuth, OpenAI keys,
  // Google Sheets credentials, and the actual email processing workflow.
  const response = await fetch(state.config.backendUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sheetId: state.config.sheetId }),
  });

  if (!response.ok) {
    throw new Error(`Backend returned ${response.status}`);
  }

  const result = await response.json();
  const messages = Array.isArray(result.messages) && result.messages.length
    ? result.messages
    : ['Backend run completed. Check your Gmail/Sheets worker logs for details.'];

  messages.forEach((message) => {
    addOutput(message);
    addLog(message);
  });
}

function normalizeBackendUrl(value) {
  return value.trim().replace(/\/$/, '');
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
