import json, numpy as np

with open('cache/latest.json') as f:
    data = json.load(f)

md = data['market_data']

def wilder_rsi(closes, n=14):
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:n])
    avg_loss = np.mean(losses[:n])
    for i in range(n, len(gains)):
        avg_gain = (avg_gain * (n-1) + gains[i]) / n
        avg_loss = (avg_loss * (n-1) + losses[i]) / n
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100/(1+rs)

watchlist = ['AAPL','META','NVDA','QQQ','TSLA','VOO','MU','MSFT','AMD','AVGO',
             'PLTR','GOOGL','AMZN','ORCL','SMH','MRVL','NOK','LITE','COHR','GLW','ADBE']

qqq_close = np.array(md['QQQ']['history']['close'])
snap_date = md['QQQ']['snapshot']['as_of']
print(f"cache_date={snap_date}")

results = []
for sym in watchlist:
    if sym not in md:
        print(f"{sym}: NOT IN CACHE")
        continue
    stock = md[sym]
    snap = stock['snapshot']
    hist = stock['history']
    closes = np.array(hist['close'])
    volumes = np.array(hist['volume'])

    pm = stock.get('premarket')
    pm_fresh = False
    pm_price = None
    if pm:
        pm_date = pm['as_of'][:10]
        if pm_date > snap['as_of']:
            pm_fresh = True
            pm_price = pm['price']

    current_price = pm_price if pm_fresh else snap['price']
    prev_close = snap['price'] if pm_fresh else (closes[-2] if len(closes) >= 2 else snap['prev_close'])

    cache_last = closes[-1]
    if abs(cache_last - snap['price']) / snap['price'] > 0.005:
        print(f"{sym}: SKIP - inconsistency close[-1]={cache_last} snap={snap['price']}")
        continue

    ma20 = float(np.mean(closes[-20:]))
    ma50 = float(np.mean(closes[-50:]))
    rsi = wilder_rsi(closes)
    vol5 = float(np.mean(volumes[-5:]))
    vol20 = float(np.mean(volumes[-20:]))
    vol_ratio = vol5 / vol20 if vol20 > 0 else 1.0

    ret_20 = (closes[-1]/closes[-21] - 1)*100 if len(closes) >= 22 else 0
    qqq_ret_20 = (qqq_close[-1]/qqq_close[-21] - 1)*100 if len(qqq_close) >= 22 else 0
    rel_str = float(ret_20 - qqq_ret_20)

    if current_price > ma20 and ma20 > ma50:
        trend = '上升↑'
    elif current_price < ma20 and ma20 < ma50:
        trend = '下降↓'
    else:
        trend = '盘整→'

    rsi_label = '⚠超买' if rsi > 70 else ('健康' if rsi >= 50 else ('偏弱' if rsi >= 30 else '超卖'))
    rel_label = '💪' if rel_str > 3 else ('👎' if rel_str < -3 else '')
    vol_label = '放量' if vol_ratio > 1.5 else ('缩量' if vol_ratio < 0.7 else '')

    recent_90 = closes[-63:] if len(closes) >= 63 else closes
    support_3m = float(np.min(recent_90))
    resist_3m = float(np.max(recent_90))
    low_2w = float(np.min(closes[-10:]))
    stop_loss = low_2w * 0.97

    recent5_low = float(np.min(closes[-5:]))
    sell_sig = False
    if current_price < ma20 and vol_ratio > 1.2 and current_price < prev_close:
        sell_sig = True
    if current_price < recent5_low * 0.99:
        sell_sig = True

    buy_conditions = 0
    if current_price > ma20: buy_conditions += 1
    if ma20 > ma50: buy_conditions += 1
    if vol_ratio > 1.5 and current_price > prev_close: buy_conditions += 1
    if 50 <= rsi <= 70: buy_conditions += 1
    if rel_str >= 0: buy_conditions += 1

    buy_sig = (not sell_sig) and (buy_conditions >= 3)

    if sell_sig:
        signal = '⚠️ 减仓警示'
    elif buy_sig:
        signal = '📈 加仓候选'
    else:
        signal = '观察/持有'

    results.append({
        'sym': sym, 'current_price': current_price, 'prev_close': prev_close,
        'snap_price': snap['price'], 'ma20': ma20, 'ma50': ma50,
        'rsi': rsi, 'rsi_label': rsi_label, 'rel_str': rel_str,
        'rel_label': rel_label, 'vol_ratio': vol_ratio, 'vol_label': vol_label,
        'trend': trend, 'signal': signal, 'sell_sig': sell_sig, 'buy_sig': buy_sig,
        'buy_conds': buy_conditions, 'pm_fresh': pm_fresh,
        'support_3m': support_3m, 'resist_3m': resist_3m,
        'low_2w': low_2w, 'stop_loss': stop_loss,
        'change_pct': snap['change_pct'],
    })

print()
header = f"{'标的':<6} {'当前价':>9} {'MA20':>8} {'MA50':>8} {'RSI(14)':>13} {'强弱vsQQQ':>11} {'趋势':>5} {'量能比':>6}  信号"
print(header)
print('-' * 105)
for r in results:
    pm_mark = '🌅' if r['pm_fresh'] else '  '
    line = (f"{r['sym']:<6} {pm_mark}${r['current_price']:>7.2f}"
            f"  ${r['ma20']:>7.2f}  ${r['ma50']:>7.2f}"
            f"  {r['rsi']:>5.1f} {r['rsi_label']:<6}"
            f"  {r['rel_str']:>+6.1f}% {r['rel_label']:<3}"
            f"  {r['trend']:<5}  {r['vol_ratio']:>4.2f}x {r['vol_label']:<4}"
            f"  {r['signal']}")
    print(line)

print()
print("=== 有信号股票明细 ===")
for r in results:
    if r['sell_sig'] or r['buy_sig']:
        print(f"{r['sym']}: {r['signal']}")
        print(f"  当前价=${r['current_price']:.2f}  MA20=${r['ma20']:.2f}  MA50=${r['ma50']:.2f}  RSI={r['rsi']:.1f}  买条件={r['buy_conds']}/5")
        print(f"  3M支撑=${r['support_3m']:.2f}  3M阻力=${r['resist_3m']:.2f}  近2周低=${r['low_2w']:.2f}  止损=${r['stop_loss']:.2f}")
        print(f"  量能比={r['vol_ratio']:.2f}x  相对强弱={r['rel_str']:+.1f}%  趋势={r['trend']}")
