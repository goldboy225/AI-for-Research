from statistics import mean

def evaluate(rows):
    tp = sum(r['malicious'] and r['blocked'] for r in rows)
    fn = sum(r['malicious'] and not r['blocked'] for r in rows)
    fp = sum(not r['malicious'] and r['blocked'] for r in rows)
    tn = sum(not r['malicious'] and not r['blocked'] for r in rows)
    ratio = lambda x, y: x/y if y else 0.0
    return dict(tp=tp, fn=fn, fp=fp, tn=tn,
        detection_rate=ratio(tp, tp+fn), false_positive_rate=ratio(fp, fp+tn),
        precision=ratio(tp, tp+fp), f1=ratio(2*tp, 2*tp+fp+fn),
        attack_success_rate=ratio(fn, tp+fn),
        mean_http_latency_ms=mean(r['http_latency_ms'] for r in rows) if rows else 0.0)
