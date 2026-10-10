"""On-chain auto-verification of crypto deposits via free public explorers/RPCs."""
import asyncio
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import httpx
from pymongo import ReturnDocument

from core import db, logger, audit, notify, now_iso, get_settings

ETH_RPC = ["https://ethereum-rpc.publicnode.com", "https://eth.llamarpc.com", "https://cloudflare-eth.com"]
BSC_RPC = ["https://bsc-dataseed.bnbchain.org", "https://bsc-dataseed1.defibit.io", "https://bsc-rpc.publicnode.com"]
TRON_API = "https://api.trongrid.io"
UTXO_API = {"BTC": "https://mempool.space/api", "LTC": "https://litecoinspace.org/api"}
TRANSFER = "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
USDT_BEP20 = "0x55d398326f99059ff775485246999027b3197955"
USDT_TRC20_HEX = "a614f803b6fd780986a42c78ec9c7f77e6ded13c"
GECKO_ID = {"BTC": "bitcoin", "LTC": "litecoin", "ETH": "ethereum", "USDT_TRC20": "tether", "USDT_BEP20": "tether"}
POLL_SECONDS = 60
GIVE_UP_HOURS = 72
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

_http: httpx.AsyncClient = None
_prices = {"at": 0, "data": {}}


def http() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=6.0), headers={"User-Agent": "CardWizard/1.0"})
    return _http


def tron_hex(addr: str) -> str:
    n = 0
    for ch in addr.strip():
        n = n * 58 + B58.index(ch)
    raw = n.to_bytes(25, "big")
    return raw[1:21].hex()


async def rpc(urls, method, params):
    err = None
    for url in urls:
        try:
            r = await http().post(url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
            r.raise_for_status()
            body = r.json()
            if body.get("error"):
                raise RuntimeError(str(body["error"]))
            return body.get("result")
        except Exception as e:
            err = e
    raise RuntimeError(f"all RPCs failed: {err}")


def _res(found=False, amount=Decimal(0), conf=0, failed=False):
    return {"found": found, "amount": amount, "confirmations": conf, "failed": failed}


async def check_utxo(coin, txid, address):
    base = UTXO_API[coin]
    r = await http().get(f"{base}/tx/{txid}")
    if r.status_code in (400, 404):
        return _res()
    r.raise_for_status()
    tx = r.json()
    sats = sum(v.get("value", 0) for v in tx.get("vout", []) if (v.get("scriptpubkey_address") or "").lower() == address.lower())
    conf = 0
    st = tx.get("status") or {}
    if st.get("confirmed"):
        tip = int((await http().get(f"{base}/blocks/tip/height")).text)
        conf = max(0, tip - int(st["block_height"]) + 1)
    return _res(True, Decimal(sats) / Decimal(10 ** 8), conf)


async def check_eth(txid, address):
    tx = await rpc(ETH_RPC, "eth_getTransactionByHash", [txid])
    if not tx:
        return _res()
    rc = await rpc(ETH_RPC, "eth_getTransactionReceipt", [txid])
    if not rc:
        return _res(True)
    if rc.get("status") != "0x1":
        return _res(True, failed=True)
    native = (tx.get("to") or "").lower() == address.lower() and tx.get("input") in ("0x", "", None)
    wei = int(tx["value"], 16) if native else 0
    head = int(await rpc(ETH_RPC, "eth_blockNumber", []), 16)
    return _res(True, Decimal(wei) / Decimal(10 ** 18), max(0, head - int(rc["blockNumber"], 16) + 1))


async def check_bep20(txid, address):
    rc = await rpc(BSC_RPC, "eth_getTransactionReceipt", [txid])
    if not rc:
        tx = await rpc(BSC_RPC, "eth_getTransactionByHash", [txid])
        return _res(bool(tx))
    if rc.get("status") != "0x1":
        return _res(True, failed=True)
    to = address.lower().removeprefix("0x")
    units = sum(int(lg["data"], 16) for lg in rc.get("logs", [])
                if (lg.get("address") or "").lower() == USDT_BEP20 and len(lg.get("topics", [])) >= 3
                and lg["topics"][0].lower().removeprefix("0x") == TRANSFER and lg["topics"][2].lower()[-40:] == to)
    head = int(await rpc(BSC_RPC, "eth_blockNumber", []), 16)
    return _res(True, Decimal(units) / Decimal(10 ** 18), max(0, head - int(rc["blockNumber"], 16) + 1))


async def check_trc20(txid, address):
    info = (await http().post(f"{TRON_API}/wallet/gettransactioninfobyid", json={"value": txid})).json()
    if not info or not info.get("blockNumber"):
        return _res()
    if (info.get("receipt") or {}).get("result") not in (None, "SUCCESS"):
        return _res(True, failed=True)
    to = tron_hex(address)
    units = sum(int(lg.get("data") or "0", 16) for lg in info.get("log", [])
                if (lg.get("address") or "").lower() == USDT_TRC20_HEX and len(lg.get("topics", [])) >= 3
                and lg["topics"][0].lower() == TRANSFER and lg["topics"][2].lower()[-40:] == to)
    now = (await http().post(f"{TRON_API}/wallet/getblock", json={"detail": False})).json()["block_header"]["raw_data"]["number"]
    return _res(True, Decimal(units) / Decimal(10 ** 6), max(0, now - int(info["blockNumber"]) + 1))


async def check_tx(coin, txid, address):
    if coin in UTXO_API:
        return await check_utxo(coin, txid, address)
    if coin == "ETH":
        return await check_eth(txid if txid.startswith("0x") else "0x" + txid, address)
    if coin == "USDT_BEP20":
        return await check_bep20(txid if txid.startswith("0x") else "0x" + txid, address)
    if coin == "USDT_TRC20":
        return await check_trc20(txid.removeprefix("0x"), address)
    raise ValueError("unsupported coin")


async def usd_price(coin) -> Decimal:
    if time.time() - _prices["at"] > 60:
        r = await http().get("https://api.coingecko.com/api/v3/simple/price",
                             params={"ids": ",".join(sorted(set(GECKO_ID.values()))), "vs_currencies": "usd"})
        r.raise_for_status()
        _prices.update(at=time.time(), data=r.json())
    return Decimal(str(_prices["data"][GECKO_ID[coin]]["usd"]))


async def _set_chain(did, **fields):
    await db.deposits.update_one({"id": did, "status": "pending"},
                                 {"$set": {f"chain.{k}": v for k, v in {**fields, "checked_at": now_iso()}.items()}})


async def process_deposit(d: dict, cfg: dict):
    did, coin = d["id"], d["coin"]
    need = int(cfg.get("confirmations", 1))
    try:
        r = await check_tx(coin, d["txid"], d["address"])
    except Exception as e:
        logger.warning(f"chain check {coin} {did}: {e}")
        return await _set_chain(did, state="checking", error="Explorer temporarily unavailable, retrying", required=need)
    if not r["found"]:
        submitted = datetime.fromisoformat(d.get("submitted_at") or d["created_at"])
        if datetime.now(timezone.utc) - submitted > timedelta(hours=GIVE_UP_HOURS):
            return await _set_chain(did, state="not_found", final=True, required=need,
                                    error="Transaction not found on-chain - needs manual review")
        return await _set_chain(did, state="searching", required=need, confirmations=0, error=None)
    if r["failed"]:
        return await _set_chain(did, state="failed", final=True, required=need, error="Transaction failed on-chain")
    if r["amount"] <= 0:
        return await _set_chain(did, state="mismatch", final=True, required=need,
                                error="Transaction does not pay the deposit address for this coin/network")
    received = str(r["amount"].normalize())
    if r["confirmations"] < need:
        return await _set_chain(did, state="confirming", confirmations=r["confirmations"], required=need,
                                received=received, error=None)
    try:
        price = await usd_price(coin)
    except Exception as e:
        logger.warning(f"price fetch failed: {e}")
        return await _set_chain(did, state="confirming", confirmations=r["confirmations"], required=need,
                                received=received, error="Price feed unavailable, retrying")
    credit = int(r["amount"] * price * 100)
    if credit <= 0:
        return await _set_chain(did, state="mismatch", final=True, required=need, received=received, error="Amount too small")
    chain = {**(d.get("chain") or {}), "state": "credited", "confirmations": r["confirmations"], "required": need,
             "received": received, "usd_price": str(price), "final": True, "error": None, "checked_at": now_iso()}
    upd = await db.deposits.find_one_and_update(
        {"id": did, "status": "pending"},
        {"$set": {"status": "approved", "credited_cents": credit, "auto": True, "reviewed_by": "auto-verify",
                  "reviewed_at": now_iso(), "chain": chain}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not upd:
        return
    await db.users.update_one({"id": d["user_id"]}, {"$inc": {"balance_cents": credit}})
    await audit({"id": None, "email": "auto-verify"}, "deposit.auto_approve", did, credit, d["user_id"],
                f"{received} {coin} @ ${price} txid {d['txid']} ref {d['reference']}")
    await notify(d["user_id"], "Deposit confirmed",
                 f"${credit / 100:.2f} ({received} {coin}) has been credited to your wallet (ref {d['reference']}).",
                 "Deposit confirmed")


async def auto_cfg(coin: str):
    s = await get_settings()
    cfg = s["auto_verify"].get(coin) or {}
    return cfg if cfg.get("enabled") else None


async def verify_now(did: str):
    d = await db.deposits.find_one({"id": did, "status": "pending"}, {"_id": 0})
    if d and (cfg := await auto_cfg(d["coin"])):
        await process_deposit(d, cfg)


async def poll_loop():
    while True:
        try:
            s = await get_settings()
            enabled = {c: v for c, v in s["auto_verify"].items() if v.get("enabled")}
            if enabled:
                q = {"status": "pending", "txid": {"$type": "string"}, "coin": {"$in": list(enabled)}, "chain.final": {"$ne": True}}
                for d in await db.deposits.find(q, {"_id": 0}).sort("submitted_at", 1).to_list(100):
                    await process_deposit(d, enabled[d["coin"]])
        except Exception as e:
            logger.error(f"auto-verify loop error: {e}")
        await asyncio.sleep(POLL_SECONDS)
