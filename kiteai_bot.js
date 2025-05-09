import fs from 'fs/promises';
import fetch from 'node-fetch';
import { SocksProxyAgent } from 'socks-proxy-agent';
import { HttpsProxyAgent } from 'https-proxy-agent';
import chalk from 'chalk';

// Konfigurasi Telegram (opsional)
const TELEGRAM_API_KEY = '';
const TELEGRAM_CHAT_ID = '';

// Tambahkan konfigurasi batas harian
const MAX_DAILY_POINTS = 200;
const POINTS_PER_INTERACTION = 10;
const MAX_DAILY_INTERACTIONS = MAX_DAILY_POINTS / POINTS_PER_INTERACTION;

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
        return data.split('\n').map(x => x.trim()).filter(Boolean);
    } catch {
        return [];
    }
}

function createAgent(proxy) {
    if (!proxy) return null;
    let url = proxy;
    if (!/^\w+:\/\//.test(proxy)) url = 'http://' + proxy;
    return url.startsWith('socks') ? new SocksProxyAgent(url) : new HttpsProxyAgent(url);
}

// Konfigurasi endpoint dan payload sesuai sample
const SAMPLES = [
    {
        name: 'prof',
        main: 'https://deployment-kazqlqgrjw8hbr8blptnpmtj.staging.gokite.ai/main',
        report: 'https://quests-usage-dev.prod.zettablock.com/api/report_usage',
        agent_id: 'deployment_UU9y1Z4Z85RAPGwkss1mUUiZ',
        message: 'What is Kite AI?'
    },
    {
        name: 'share',
        main: 'https://deployment-tqgv8vboiwipbkgsmzgdmwpm.staging.gokite.ai/main',
        report: 'https://quests-usage-dev.prod.zettablock.com/api/report_usage',
        agent_id: 'deployment_ECz5O55dH0dBQaGKuT47kzYC',
        message: 'What do you think of this transaction? 0x252c02bded9a24426219248c9c1b065b752d3cf8bedf4902ed62245ab950895b'
    },
    {
        name: 'crypto_buddy',
        main: 'https://deployment-0ovyzutzgttaydzu6eqn9bxi.staging.gokite.ai/main',
        report: 'https://quests-usage-dev.prod.zettablock.com/api/report_usage',
        agent_id: 'deployment_fseGykIvCLs3m9Nrpe9Zguy9',
        message: 'Price of bitcoin'
    }
    // Endpoint inference dan stats dibangun dinamis dari interaction_id hasil response step 2
];

// Header umum
function getHeaders(type = 'main') {
    const base = {
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://agents.testnet.gokite.ai',
        'priority': 'u=1, i',
        'referer': 'https://agents.testnet.gokite.ai/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    };
    if (type === 'main') {
        return {
            ...base,
            'accept': 'text/event-stream',
            'content-type': 'application/json',
        };
    } else if (type === 'report') {
        return {
            ...base,
            'accept': '*/*',
            'content-type': 'application/json',
        };
    } else {
        return {
            ...base,
            'accept': '*/*',
        };
    }
}

async function getDailyPoints(wallet, proxy) {
    const url = 'https://api-kiteai.bonusblock.io/api/kite-ai/get-status';
    const headers = {
        'accept': 'application/json, text/plain, */*',
        // 'x-auth-token': 'TOKEN_WALLET', // sesuaikan jika perlu
    };
    const agent = createAgent(proxy);
    try {
        const res = await fetch(url, { headers, agent });
        const text = await res.text();
        if (!res.ok) {
            console.log(chalk.red(`[${wallet}] API status: ${res.status}`));
            console.log(chalk.red(`[${wallet}] Raw response: ${text}`));
            return 0;
        }
        let data;
        try {
            data = JSON.parse(text);
        } catch (e) {
            console.log(chalk.red(`[${wallet}] Gagal parse JSON: ${e.message}`));
            console.log(chalk.red(`[${wallet}] Raw response: ${text}`));
            return 0;
        }
        return data?.payload?.dailyAgentActionsXp || 0;
    } catch (e) {
        console.log(chalk.red(`[${wallet}] Gagal cek daily point: ${e.message}`));
        return 0;
    }
}

async function runSample(sample, wallet, proxy, walletState) {
    if (walletState.dailyPoints >= MAX_DAILY_POINTS) {
        console.log(chalk.yellow(`[${sample.name}] Wallet ${wallet} sudah mencapai max daily points (${MAX_DAILY_POINTS}), skip...`));
        return;
    }
    const agent = createAgent(proxy);
    try {
        // Step 1: /main
        const mainRes = await fetch(sample.main, {
            method: 'POST',
            headers: getHeaders('main'),
            agent,
            body: JSON.stringify({ message: sample.message, stream: true })
        });
        const mainText = await mainRes.text();
        console.log(chalk.green(`[${sample.name}] Step 1 /main response: `), mainText.slice(0, 200));

        // Step 2: /report_usage
        const reportRes = await fetch(sample.report, {
            method: 'POST',
            headers: getHeaders('report'),
            agent,
            body: JSON.stringify({ wallet_address: wallet, agent_id: sample.agent_id, request_text: sample.message, response_text: mainText, request_metadata: {} })
        });
        const reportText = await reportRes.text();
        console.log(chalk.green(`[${sample.name}] Step 2 /report_usage response: `), reportText.slice(0, 200));

        // Ambil interaction_id dari response step 2
        let interaction_id = null;
        try {
            const reportJson = JSON.parse(reportText);
            interaction_id = reportJson.interaction_id;
        } catch (e) {
            console.log(chalk.red(`[${sample.name}] Gagal parsing interaction_id dari response step 2`));
        }
        if (!interaction_id) {
            console.log(chalk.red(`[${sample.name}] interaction_id tidak ditemukan, skip step 3-5`));
            return;
        }

        // Step 3: /inference dengan interaction_id
        const inferenceUrl = `https://neo.prod.zettablock.com/v1/inference?id=${interaction_id}`;
        const infRes = await fetch(inferenceUrl, { headers: getHeaders('inference'), agent });
        const infText = await infRes.text();
        console.log(chalk.green(`[${sample.name}] Step 3 /inference response: `), infText.slice(0, 200));

        // Step 4: /inference (ulang) dengan interaction_id
        const infRes2 = await fetch(inferenceUrl, { headers: getHeaders('inference'), agent });
        const infText2 = await infRes2.text();
        console.log(chalk.green(`[${sample.name}] Step 4 /inference response: `), infText2.slice(0, 200));

        // Step 5: /stats dengan wallet address
        const statsUrl = `https://quests-usage-dev.prod.zettablock.com/api/user/${wallet}/stats`;
        const statsRes = await fetch(statsUrl, { headers: getHeaders('stats'), agent });
        const statsText = await statsRes.text();
        console.log(chalk.green(`[${sample.name}] Step 5 /stats response: `), statsText.slice(0, 200));

        // Tambah poin harian wallet
        walletState.dailyPoints += POINTS_PER_INTERACTION;

        // (Opsional) Kirim ke Telegram
        await sendTelegramMessage(`Bot ${sample.name} untuk wallet ${wallet} selesai!`);
    } catch (e) {
        console.log(chalk.red(`[${sample.name}] Error: `), e.message);
    }
}

async function main() {
    const wallets = await loadList('wallets.txt');
    const proxies = await loadList('proxies.txt');
    if (wallets.length === 0) {
        console.log(chalk.red('Tidak ada wallet di wallets.txt'));
        return;
    }

    // Loop harian
    while (true) {
        // State harian per wallet
        const walletStates = {};
        for (const wallet of wallets) {
            walletStates[wallet] = { dailyPoints: 0 };
        }

        // Jalankan semua wallet paralel
        await Promise.all(wallets.map(async (wallet) => {
            const proxy = proxies.length > 0 ? proxies[Math.floor(Math.random() * proxies.length)] : null;
            for (const sample of SAMPLES) {
                await runSample(sample, wallet, proxy, walletStates[wallet]);
                if (walletStates[wallet].dailyPoints >= MAX_DAILY_POINTS) {
                    console.log(chalk.yellow(`[${wallet}] Sudah mencapai max daily points (${MAX_DAILY_POINTS}), skip sisa sample.`));
                    break;
                }
            }
        }));

        // Setelah semua wallet selesai, delay 24 jam
        console.log(chalk.cyan('Semua wallet sudah mencapai max daily points. Menunggu 24 jam sebelum reset...'));
        await new Promise(resolve => setTimeout(resolve, 24 * 60 * 60 * 1000));
    }
}

main(); 