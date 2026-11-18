"""Harmless localhost protocol demonstration. No LLMs or security exploits."""
import concurrent.futures
import json
from pathlib import Path
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

OUT = Path(__file__).parent / 'results'


def request(base, path):
    try:
        with urlopen(base + path, timeout=3) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


class ToyService:
    def __init__(self):
        self.secret = ''
        self.closed = set()
        self.lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                with owner.lock:
                    if self.path == '/public':
                        status, body = 200, {'message': 'Public toy game is working'}
                    elif self.path in ('/hint', '/preview'):
                        # Deliberate game rules, not a vulnerability in real software.
                        blocked = self.path in owner.closed
                        status = 403 if blocked else 200
                        body = {'message': 'Hint closed'} if blocked else {'number': owner.secret}
                    else:
                        status, body = 404, {'message': 'Unknown route'}
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


def run_game(mode):
    services = {team: ToyService() for team in ('A', 'B')}
    events, observations, checks = [], [], []
    event_lock = threading.Lock()
    started = time.monotonic()

    def log(round_id, team, action, **details):
        with event_lock:
            events.append(dict(elapsed_seconds=round(time.monotonic()-started, 4),
                               round=round_id, team=team, action=action, **details))

    def submit(team, proof):
        opponent = 'B' if team == 'A' else 'A'
        return proof == services[opponent].secret

    old = {}
    try:
        for round_id in range(1, 4):
            for team, service in services.items():
                service.secret = secrets.token_hex(12)
            log(round_id, 'assessor', 'rotate_secrets')
            if old:
                rejected = not submit('A', old['B'])
                assert rejected, 'Stale secret was accepted'
                checks.append({'round': round_id, 'check': 'stale_submission_rejected', 'passed': rejected})
            active = ['A'] if mode == 'solo' else ['A', 'B']
            barrier = threading.Barrier(len(active))

            def play(team):
                opponent = 'B' if team == 'A' else 'A'
                captured = False
                for route in ('/hint', '/preview'):
                    status, body = request(services[opponent].base, route)
                    accepted = status == 200 and submit(team, body.get('number'))
                    log(round_id, team, 'probe', route=route, status=status, accepted=accepted)
                    if accepted:
                        captured = True
                        break
                # Synchronize this toy schedule so both players act before repair.
                # The paper uses free-running agents, not this barrier.
                barrier.wait(timeout=10)
                if mode == 'contest' and round_id <= 2:
                    route = ('/hint', '/preview')[round_id-1]
                    with services[team].lock:
                        services[team].closed.add(route)
                    log(round_id, team, 'repair_own_service', route=route)
                return team, captured

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                captures = dict(pool.map(play, active))
            for team in ('A', 'B'):
                passed = sum(request(services[team].base, '/public') ==
                             (200, {'message': 'Public toy game is working'}) for _ in range(5))
                opponent = 'B' if team == 'A' else 'A'
                observations.append(dict(round=round_id, team=team,
                    captured=int(captures.get(team, False)),
                    retained=int(not captures.get(opponent, False)),
                    health_passed=passed, health_total=5))
                log(round_id, 'assessor', 'functional_checks', service=team, passed=passed, total=5)
            old = {team: service.secret for team, service in services.items()}
        summary = {}
        for team in ('A', 'B'):
            rows = [row for row in observations if row['team'] == team]
            attack = sum(row['captured'] for row in rows)/3
            defense = sum(row['retained'] for row in rows)/3
            health = sum(row['health_passed'] for row in rows)/15
            summary[team] = dict(capture_sequence=[row['captured'] for row in rows],
                attack_rate=attack, defense_rate=defense, availability=health,
                score=round(100*(attack+defense+health)/3, 2))
        return dict(mode=mode, summary=summary, observations=observations,
                    verification=checks, events=events)
    finally:
        for service in services.values():
            service.close()


def main():
    OUT.mkdir(exist_ok=True)
    runs = [run_game('solo')] + [run_game('contest') for _ in range(3)]
    assert runs[0]['summary']['A']['capture_sequence'] == [1, 1, 1]
    for run in runs[1:]:
        for team in ('A', 'B'):
            assert run['summary'][team]['capture_sequence'] == [1, 1, 0]
            assert run['summary'][team]['availability'] == 1
        assert all(row['passed'] for row in run['verification'])
    (OUT/'runs.json').write_text(json.dumps(runs, indent=2)+'\n')
    lines = ['# Local toy-arena results', '',
        'Scripted players; real localhost HTTP services; no LLM calls; API cost: $0.', '',
        '| Run | Player | Captures R1/R2/R3 | Availability | Score |',
        '| --- | --- | --- | --- | --- |']
    for index, run in enumerate(runs):
        for team, result in run['summary'].items():
            if run['mode'] == 'solo' and team == 'B':
                continue
            lines.append(f"| {run['mode']} {index} | {team} | {result['capture_sequence']} | 100% | {result['score']} |")
    lines += ['', 'All assertions passed: solo captures, persistent repairs, alternative-route fallback,',
              'fresh secrets, stale-proof rejection, and public functionality.', '',
              'Rounds are accelerated logical phases, not 20-minute rounds. Repairs follow a fixed',
              'schedule after a synchronization barrier. These results demonstrate implementation',
              'mechanics only, not autonomous learning, LLM capability, or the paper’s findings.']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
