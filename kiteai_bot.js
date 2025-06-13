import fs from 'fs/promises';
import fetch from 'node-fetch';
import { SocksProxyAgent } from 'socks-proxy-agent';
import { HttpsProxyAgent } from 'https-proxy-agent';
import chalk from 'chalk';
import { Worker, isMainThread, parentPort, workerData } from 'worker_threads';
import os from 'os';
import { ethers } from 'ethers';
import signatures from './signatures.json' assert { type: 'json' };
import sessions from './sessions.json' assert { type: 'json' };

// Konfigurasi Telegram (opsional)
const TELEGRAM_API_KEY = '';
const TELEGRAM_CHAT_ID = '';

// Tambahkan konfigurasi batas harian
const MAX_DAILY_POINTS = 200;
const POINTS_PER_INTERACTION = 10;
const MAX_DAILY_INTERACTIONS = MAX_DAILY_POINTS / POINTS_PER_INTERACTION;

// Konfigurasi API
const API_CONFIG = {
    ozone: 'https://ozone-point-system.prod.gokite.ai/agent/inference',
    rpc: 'https://rpc-testnet.gokite.ai/',
    neo: 'https://neo.prod.gokite.ai',
    contract: '0x948f52524Bdf595b439e7ca78620A8f843612df3'
};

// Konfigurasi samples dengan service_id yang benar
const SAMPLES = [
    {
        name: 'prof',
        service_id: 'deployment_KiMLvUiTydioiHm7PWZ12zJU',
        message: 'What is Kite AI?'
    },
    {
        name: 'prof',
        service_id: 'deployment_KiMLvUiTydioiHm7PWZ12zJU',
        message: "Tell me about the latest updates in Kite AI"
    },
    {
        name: 'prof',
        service_id: 'deployment_KiMLvUiTydioiHm7PWZ12zJU',
        message: "What are the upcoming features in Kite AI?"
    },
    {
        name: 'prof',
        service_id: 'deployment_KiMLvUiTydioiHm7PWZ12zJU',
        message: "How can Kite AI improve my development workflow?"
    },
    {
        name: 'prof',
        service_id: 'deployment_KiMLvUiTydioiHm7PWZ12zJU',
        message: "What makes Kite AI unique in the market?"
    },
    {
        name: 'prof',
        service_id: 'deployment_KiMLvUiTydioiHm7PWZ12zJU',
        message: "How does Kite AI handle code completion?"
    },
    {
        name: 'prof',
        service_id: 'deployment_KiMLvUiTydioiHm7PWZ12zJU',
        message: "Can you explain Kite AI's machine learning capabilities?"
    },
    {
        name: 'prof',
        service_id: 'deployment_KiMLvUiTydioiHm7PWZ12zJU',
        message: "What programming languages does Kite AI support best?"
    },
    {
        name: 'prof',
        service_id: 'deployment_KiMLvUiTydioiHm7PWZ12zJU',
        message: "How does Kite AI integrate with different IDEs?"
    },
    {
        name: 'prof',
        service_id: 'deployment_KiMLvUiTydioiHm7PWZ12zJU',
        message: "What are the advanced features of Kite AI?"
    },
    {
        name: 'share',
        service_id: 'deployment_OX7sn2D0WvxGUGK8CTqsU5VJ',
        message: 'What do you think of this transaction? 0x252c02bded9a24426219248c9c1b065b752d3cf8bedf4902ed62245ab950895b'
    },
    {
        name: 'crypto_buddy',
        service_id: 'deployment_nXOmSXjGYfDOCO6iHSw9GKRk',
        message: 'Price of bitcoin'
    },
    {
        name: 'crypto_buddy',
        service_id: 'deployment_nXOmSXjGYfDOCO6iHSw9GKRk',
        message: "What's the current market sentiment for Solana?"
    },
    {
        name: 'crypto_buddy',
        service_id: 'deployment_nXOmSXjGYfDOCO6iHSw9GKRk',
        message: "Analyze Bitcoin's price movement in the last hour"
    },
    {
        name: 'crypto_buddy',
        service_id: 'deployment_nXOmSXjGYfDOCO6iHSw9GKRk',
        message: "Compare ETH and BTC performance today"
    },
    {
        name: 'crypto_buddy',
        service_id: 'deployment_nXOmSXjGYfDOCO6iHSw9GKRk',
        message: "Which altcoins are showing bullish patterns?"
    },
    {
        name: 'crypto_buddy',
        service_id: 'deployment_nXOmSXjGYfDOCO6iHSw9GKRk',
        message: "Market analysis for top 10 cryptocurrencies"
    },
    {
        name: 'crypto_buddy',
        service_id: 'deployment_nXOmSXjGYfDOCO6iHSw9GKRk',
        message: "Technical analysis for Polkadot"
    },
    {
        name: 'crypto_buddy',
        service_id: 'deployment_nXOmSXjGYfDOCO6iHSw9GKRk',
        message: "Price movement patterns for Avalanche"
    },
    {
        name: 'crypto_buddy',
        service_id: 'deployment_nXOmSXjGYfDOCO6iHSw9GKRk',
        message: "Polygon's market performance analysis"
    },
    {
        name: 'crypto_buddy',
        service_id: 'deployment_nXOmSXjGYfDOCO6iHSw9GKRk',
        message: "Latest developments affecting BNB price"
    },
    {
        name: 'crypto_buddy',
        service_id: 'deployment_nXOmSXjGYfDOCO6iHSw9GKRk',
        message: "Cardano's market outlook"
    },
];

// Helper untuk mengirim pesan ke Telegram
async function sendTelegramMessage(message) {
    if (!TELEGRAM_API_KEY || !TELEGRAM_CHAT_ID) return;
    const url = `https://api.telegram.org/bot${TELEGRAM_API_KEY}/sendMessage`;
    const payload = { chat_id: TELEGRAM_CHAT_ID, text: message, parse_mode: 'Markdown' };
    try {
        await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    } catch (e) {
        console.log(chalk.red('[TELEGRAM ERROR]'), e.message);
    }
}

// Membaca file wallets.txt dan proxies.txt
async function loadList(filename) {
    try {
        const data = await fs.readFile(filename, 'utf8');
        const lines = data.split('\n').map(x => x.trim()).filter(Boolean);
        console.log(chalk.cyan(`Loaded ${filename}:`));
        lines.forEach((line, index) => {
            console.log(chalk.cyan(`[${index + 1}] ${line}`));
        });
        return lines;
    } catch (e) {
        console.log(chalk.red(`Error loading ${filename}: ${e.message}`));
        return [];
    }
}

function createAgent(proxy) {
    if (!proxy) return null;
    let url = proxy;
    if (!/^\w+:\/\//.test(proxy)) url = 'http://' + proxy;
    return url.startsWith('socks') ? new SocksProxyAgent(url) : new HttpsProxyAgent(url);
}

// Header umum
function getHeaders(type = 'main', token = '') {
    const base = {
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://testnet.gokite.ai',
        'referer': 'https://testnet.gokite.ai/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    };

    if (token) {
        base['Authorization'] = `Bearer ${token}`;
    }

    if (type === 'main') {
        return {
            ...base,
            'accept': 'text/event-stream',
            'content-type': 'application/json',
        };
    } else if (type === 'rpc') {
        return {
            ...base,
            'content-type': 'application/json',
        };
    } else {
        return {
            ...base,
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
        };
    }
}

async function checkAndRefreshToken(wallet, proxy, token) {
    try {
        // Test token validity with a simple API call
        const testRes = await fetch(`${API_CONFIG.neo}/v1/user/me`, {
            headers: getHeaders('verify', token),
            agent: createAgent(proxy)
        });

        if (testRes.status === 401 || testRes.status === 403) {
            console.log(chalk.yellow(`[${wallet}] Token expired, refreshing...`));
            // Get new token
            const newToken = await getAccessToken(wallet, proxy);
            if (newToken) {
                console.log(chalk.green(`[${wallet}] Successfully refreshed token`));
                return newToken;
            }
            return null;
        }
        return token;
    } catch (e) {
        console.log(chalk.red(`[${wallet}] Error checking token: ${e.message}`));
        return null;
    }
}

async function runSample(sample, wallet, proxy, walletState, token) {
    if (walletState.interactions >= MAX_DAILY_INTERACTIONS) {
        console.log(chalk.yellow(`[${sample.name}] Wallet ${wallet} sudah mencapai max daily points (${MAX_DAILY_POINTS}), skip...`));
        return;
    }

    const agent = createAgent(proxy);
    try {
        // Check and refresh token if needed before making requests
        token = await checkAndRefreshToken(wallet, proxy, token);
        if (!token) {
            console.log(chalk.red(`[${sample.name}] Failed to get valid token, skipping...`));
            return;
        }

        // Step 1: Inference Request
        const inferenceRes = await fetch(API_CONFIG.ozone, {
            method: 'POST',
            headers: getHeaders('main', token),
            agent,
            body: JSON.stringify({
                service_id: sample.service_id,
                subnet: "kite_ai_labs",
                stream: true,
                body: {
                    stream: true,
                    message: sample.message
                }
            })
        });

        // Check for unauthorized response
        if (inferenceRes.status === 401 || inferenceRes.status === 403) {
            console.log(chalk.yellow(`[${sample.name}] Token expired during inference, refreshing...`));
            token = await getAccessToken(wallet, proxy);
            if (!token) {
                console.log(chalk.red(`[${sample.name}] Failed to refresh token, skipping...`));
                return;
            }
            // Retry the inference request with new token
            inferenceRes = await fetch(API_CONFIG.ozone, {
                method: 'POST',
                headers: getHeaders('main', token),
                agent,
                body: JSON.stringify({
                    service_id: sample.service_id,
                    subnet: "kite_ai_labs",
                    stream: true,
                    body: {
                        stream: true,
                        message: sample.message
                    }
                })
            });
        }
        // Tangkap seluruh response eventStream sebagai string mentah
        const raw = await inferenceRes.text();
        let inferenceText = "";
        const lines = raw.split('\n');
        for (const line of lines) {
            if (line.startsWith('data: ') && line !== 'data: [DONE]') {
                try {
                    const json = JSON.parse(line.slice(6));
                    const content = json.choices?.[0]?.delta?.content;
                    if (content) inferenceText += content;
                } catch (e) {
                    // skip jika bukan JSON valid
                }
            }
        }
        console.log(chalk.green(`[${sample.name}] Step 1 inference response:`), inferenceText.slice(0, 200));

        // Step 2: Wallet Verification
        const rpcRes = await fetch(API_CONFIG.rpc, {
            method: 'POST',
            headers: getHeaders('rpc'),
            agent,
            body: JSON.stringify({
                jsonrpc: "2.0",
                id: 1,
                method: "eth_call",
                params: [{
                    data: "0x8cb84e18000000000000000000000000" + wallet.slice(2) + "4b6f5b36bb7706150b17e2eecb6e602b1b90b94a4bf355df57466626a5cb897b",
                    to: API_CONFIG.contract
                }, "latest"]
            })
        });
        const rpcText = await rpcRes.text();
        console.log(chalk.green(`[${sample.name}] Step 2 RPC response: `), rpcText.slice(0, 200));

        // Step 3: Submit Receipt
        const receiptPayload = {
            address: wallet,
            service_id: sample.service_id,
            input: [{ type: "text/plain", value: sample.message }],
            output: [{ type: "text/plain", value: inferenceText }]
        };
        console.log(chalk.blue(`[${sample.name}] Step 3 submit_receipt request input:`), receiptPayload.input);
        console.log(chalk.blue(`[${sample.name}] Step 3 submit_receipt request output:`), receiptPayload.output);
        const receiptRes = await fetch(`${API_CONFIG.neo}/v2/submit_receipt`, {
            method: 'POST',
            headers: getHeaders('receipt', token),
            agent,
            body: JSON.stringify(receiptPayload)
        });
        const receiptText = await receiptRes.text();
        console.log(chalk.green(`[${sample.name}] Step 3 receipt response: `), receiptText.slice(0, 200));

        // Step 4: Verify Inference
        let interactionId = null;
        try {
            const receiptJson = JSON.parse(receiptText);
            interactionId = receiptJson.interaction_id;
        } catch (e) {
            console.log(chalk.red(`[${sample.name}] Gagal parsing interaction_id`));
        }

        if (interactionId) {
            const verifyRes = await fetch(`${API_CONFIG.neo}/v1/inference?id=${interactionId}`, {
                headers: getHeaders('verify', token),
                agent
            });
            const verifyText = await verifyRes.text();
            console.log(chalk.green(`[${sample.name}] Step 4 verify response: `), verifyText.slice(0, 200));
        }

        // Update wallet state
        walletState.interactions++;
        walletState.dailyPoints = walletState.interactions * POINTS_PER_INTERACTION;

        // (Opsional) Kirim ke Telegram
        await sendTelegramMessage(`Bot ${sample.name} untuk wallet ${wallet} selesai! Points: ${walletState.dailyPoints}`);
    } catch (e) {
        console.log(chalk.red(`[${sample.name}] Error: `), e.message);
    }
}

// Fungsi untuk menyimpan state wallet
async function saveWalletState(walletStates) {
    try {
        await fs.writeFile('wallet_states.json', JSON.stringify(walletStates, null, 2));
    } catch (e) {
        console.log(chalk.red('Error saving wallet state:', e.message));
    }
}

// Fungsi untuk memuat state wallet
async function loadWalletState() {
    try {
        const data = await fs.readFile('wallet_states.json', 'utf8');
        return JSON.parse(data);
    } catch {
        return {};
    }
}

// Fungsi untuk mengecek apakah wallet perlu direset (24 jam)
function shouldResetWallet(walletState) {
    if (!walletState.lastReset) return true;
    const now = new Date().getTime();
    const lastReset = new Date(walletState.lastReset).getTime();
    return (now - lastReset) >= 24 * 60 * 60 * 1000; // 24 jam dalam milliseconds
}

// Fungsi untuk mendapatkan signature (dari konfigurasi, bukan signMessage)
async function getSignature(wallet, proxy) {
    // Ambil signature dari file signatures.json berdasarkan wallet
    const sig = signatures[wallet.toLowerCase()];
    if (!sig) {
        console.log(chalk.red(`[${wallet}] Signature not found in signatures.json!`));
        return null;
    }
    console.log(chalk.green(`[${wallet}] Using static signature from config`));
    return sig;
}

// Fungsi untuk mendapatkan access token
async function getAccessToken(wallet, proxy) {
    const agent = createAgent(proxy);
    try {
        // Dapatkan signature terlebih dahulu
        const signature = await getSignature(wallet, proxy);
        if (!signature) {
            console.log(chalk.red(`[${wallet}] Failed to get signature`));
            return null;
        }

        console.log(chalk.yellow(`Using signature: ${signature}`));

        // Gunakan value neo_session dan refresh_token dari sessions.json per wallet
        const sessionConfig = sessions[wallet.toLowerCase()] || {};
        const neoSession = sessionConfig.neoSession || '';
        const refreshToken = sessionConfig.refreshToken || '';

        const signinRes = await fetch('https://neo.prod.gokite.ai/v2/signin', {
            method: 'POST',
            headers: {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'authorization': signature,
                'content-type': 'application/json',
                'origin': 'https://testnet.gokite.ai',
                'referer': 'https://testnet.gokite.ai/',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'cookie': `neo_session=${neoSession}; refresh_token=${refreshToken}`
            },
            agent,
            body: JSON.stringify({
                eoa: wallet
            })
        });

        const signinData = await signinRes.json();
        if (signinData.error) {
            console.log(chalk.red(`[${wallet}] Signin error: ${signinData.error}`));
            return null;
        }

        // Save the access token to sessions.json
        if (signinData.data && signinData.data.access_token) {
            sessions[wallet.toLowerCase()] = {
                ...sessions[wallet.toLowerCase()],
                accessToken: signinData.data.access_token,
                neoSession: neoSession,
                refreshToken: refreshToken
            };
            
            // Write updated sessions to file
            try {
                await fs.writeFile('sessions.json', JSON.stringify(sessions, null, 2));
                console.log(chalk.green(`[${wallet}] Successfully saved access token to sessions.json`));
            } catch (e) {
                console.log(chalk.red(`[${wallet}] Failed to save access token: ${e.message}`));
            }
        }

        console.log(chalk.green(`[${wallet}] Successfully got access token`));
        return signinData.data.access_token;
    } catch (e) {
        console.log(chalk.red(`[${wallet}] Failed to get access token: ${e.message}`));
        return null;
    }
}

async function runWallet(wallet, proxy) {
    let walletState = { interactions: 0, dailyPoints: 0 };
    let token = await getAccessToken(wallet, proxy);
    if (!token) return;
    for (const sample of SAMPLES) {
        // Jika sudah 200 point, stop dan lanjut ke wallet berikutnya
        if (walletState.dailyPoints >= MAX_DAILY_POINTS) {
            console.log(chalk.yellow(`[${wallet}] Sudah mencapai ${MAX_DAILY_POINTS} point, berhenti dan lanjut ke wallet berikutnya.`));
            break;
        }
        await runSample(sample, wallet, proxy, walletState, token);
    }
}

// Worker thread function
async function workerFunction() {
    const { wallet, proxy, samples } = workerData;
    const walletState = { 
        dailyPoints: 0,
        interactions: 0,
        lastReset: new Date().toISOString()
    };
    
    // Get access token first
    const token = await getAccessToken(wallet, proxy);
    if (!token) {
        console.log(chalk.red(`[${wallet}] Skipping due to failed token retrieval`));
        return;
    }
    
    for (const sample of samples) {
        if (walletState.dailyPoints >= MAX_DAILY_POINTS) {
            console.log(chalk.yellow(`[${wallet}] Sudah mencapai ${MAX_DAILY_POINTS} point, berhenti dan lanjut ke wallet berikutnya.`));
            break;
        }
        await runSample(sample, wallet, proxy, walletState, token);
    }
    
    parentPort.postMessage({ 
        wallet, 
        status: 'completed', 
        points: walletState.dailyPoints,
        interactions: walletState.interactions,
        lastReset: walletState.lastReset
    });
}

// Main thread function
async function main() {
    if (!isMainThread) {
        await workerFunction();
        return;
    }

    const wallets = await loadList('wallets.txt');
    const proxies = await loadList('proxies.txt');
    if (wallets.length === 0) {
        console.log(chalk.red('Tidak ada wallet di wallets.txt'));
        return;
    }

    // Load previous wallet states
    let walletStates = await loadWalletState();
    
    // Calculate number of workers (use 75% of available CPU cores)
    const numWorkers = Math.max(1, Math.floor(os.cpus().length * 0.75));
    console.log(chalk.cyan(`Using ${numWorkers} worker threads`));

    // Filter dan reset wallet yang sudah 24 jam
    const activeWallets = wallets.filter(wallet => {
        const state = walletStates[wallet] || { 
            dailyPoints: 0, 
            interactions: 0,
            lastReset: new Date().toISOString()
        };
        
        if (shouldResetWallet(state)) {
            walletStates[wallet] = {
                dailyPoints: 0,
                interactions: 0,
                lastReset: new Date().toISOString()
            };
            console.log(chalk.yellow(`[${wallet}] Reset state setelah 24 jam`));
            return true;
        }
        
        return state.interactions < MAX_DAILY_INTERACTIONS;
    });

    if (activeWallets.length === 0) {
        console.log(chalk.cyan('Semua wallet sudah mencapai max daily points.'));
        return;
    }

    // Process wallets in batches
    for (let i = 0; i < activeWallets.length; i += numWorkers) {
        const batch = activeWallets.slice(i, i + numWorkers);
        const workers = batch.map(wallet => {
            const proxy = proxies.length > 0 ? proxies[Math.floor(Math.random() * proxies.length)] : null;
            return new Promise((resolve, reject) => {
                const worker = new Worker(new URL(import.meta.url), {
                    workerData: { wallet, proxy, samples: SAMPLES }
                });
                
                worker.on('message', (message) => {
                    if (message.status === 'completed') {
                        walletStates[message.wallet] = {
                            dailyPoints: message.points,
                            interactions: message.interactions,
                            lastReset: message.lastReset
                        };
                        saveWalletState(walletStates);
                        console.log(chalk.green(`[${message.wallet}] Completed with ${message.points} points (${message.interactions} interactions)`));
                    }
                    resolve();
                });
                
                worker.on('error', reject);
                worker.on('exit', (code) => {
                    if (code !== 0) reject(new Error(`Worker stopped with exit code ${code}`));
                });
            });
        });

        await Promise.all(workers);
    }
}

main(); 