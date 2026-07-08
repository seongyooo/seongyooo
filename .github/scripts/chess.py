#!/usr/bin/env python3
import chess
import chess.svg
import os
import re
import json
import random
import urllib.request
import urllib.error

REPO_OWNER = "seongyooo"
REPO_NAME  = "seongyooo"
FEN_FILE        = "chess/game.fen"
SVG_FILE        = "chess/board.svg"
LAST_EVENT_FILE = "chess/last_event_id.txt"
README_FILE     = "README.md"
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "")


# ── GitHub API ──────────────────────────────────────────────────────────────

def api_get(url):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"token {GITHUB_TOKEN}")
    req.add_header("User-Agent", "chess-bot/1.0")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def get_push_events():
    return api_get(f"https://api.github.com/users/{REPO_OWNER}/events?per_page=100")


# ── Board I/O ────────────────────────────────────────────────────────────────

def load_board():
    if os.path.exists(FEN_FILE):
        fen = open(FEN_FILE).read().strip()
        if fen:
            try:
                return chess.Board(fen)
            except Exception:
                pass
    return chess.Board()

def save_board(board):
    os.makedirs("chess", exist_ok=True)
    open(FEN_FILE, "w").write(board.fen())
    lastmove = board.peek() if board.move_stack else None
    svg = chess.svg.board(board, lastmove=lastmove, size=420)
    open(SVG_FILE, "w").write(svg)

def load_last_id():
    if os.path.exists(LAST_EVENT_FILE):
        v = open(LAST_EVENT_FILE).read().strip()
        return v if v else None
    return None

def save_last_id(eid):
    open(LAST_EVENT_FILE, "w").write(str(eid))


# ── Chess logic ──────────────────────────────────────────────────────────────

def make_move(board):
    """Random legal move; prefers captures and checks for fun."""
    legal = list(board.legal_moves)
    if not legal:
        return None
    captures = [m for m in legal if board.is_capture(m)]
    checks   = [m for m in legal if board.gives_check(m)]
    pool = checks or captures or legal
    move = random.choice(pool)
    board.push(move)
    return move

def status_line(board):
    if board.is_checkmate():
        who = "⬛ Black" if board.turn == chess.WHITE else "⬜ White"
        return f"🏆 **체크메이트! {who} 승리!**"
    if board.is_stalemate():
        return "🤝 **스테일메이트 — 무승부**"
    if board.is_insufficient_material():
        return "🤝 **기물 부족 — 무승부**"
    turn = "⬜ White" if board.turn == chess.WHITE else "⬛ Black"
    check = " ⚠️ 체크!" if board.is_check() else ""
    return f"**{turn}의 차례{check}**"


# ── README update ────────────────────────────────────────────────────────────

def move_history_str(board):
    history, tmp = [], chess.Board()
    for m in board.move_stack:
        history.append(tmp.san(m))
        tmp.push(m)
    recent = history[-6:] if len(history) > 6 else history
    return " → ".join(recent) if recent else "없음"

def update_readme(board):
    content = open(README_FILE, "r", encoding="utf-8").read()

    section = f"""<!-- CHESS_START -->
## ♟️ Chess — 커밋하면 수가 자동으로 놓여요!

> 내가 어느 레포에든 커밋할 때마다 체스 수가 자동으로 반영돼요 🤖

![Chess Board](./chess/board.svg)

{status_line(board)}

| | |
|---|---|
| 총 수 | {len(board.move_stack)}수 |
| 최근 수 | {move_history_str(board)} |

<!-- CHESS_END -->"""

    if "<!-- CHESS_START -->" in content:
        new_content = re.sub(
            r"<!-- CHESS_START -->.*?<!-- CHESS_END -->",
            section,
            content,
            flags=re.DOTALL,
        )
    else:
        new_content = content.rstrip() + "\n\n" + section + "\n"

    open(README_FILE, "w", encoding="utf-8").write(new_content)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    board    = load_board()
    last_id  = load_last_id()
    events   = get_push_events()

    if not events:
        print("이벤트 없음")
        save_board(board)
        update_readme(board)
        return

    latest_id = events[0]["id"]

    # 첫 실행: 기준점만 저장하고 종료
    if last_id is None:
        print(f"초기화 완료 — 기준 이벤트 ID: {latest_id}")
        save_last_id(latest_id)
        save_board(board)
        update_readme(board)
        return

    # 새 push 이벤트 수집
    new_pushes = []
    for e in events:
        if e["id"] == last_id:
            break
        if e["type"] == "PushEvent":
            new_pushes.append(e)

    if not new_pushes:
        print("새 커밋 없음")
        return

    print(f"새 push {len(new_pushes)}개 → 최대 3수 반영")
    save_last_id(latest_id)

    moves_made = 0
    for _ in range(min(len(new_pushes), 3)):
        if board.is_game_over():
            print("게임 종료 → 새 게임 시작")
            board = chess.Board()
        move = make_move(board)
        if move:
            san = chess.Board(board.fen())
            print(f"  수 반영: {move.uci()}")
            moves_made += 1

    print(f"총 {moves_made}수 반영")
    save_board(board)
    update_readme(board)


if __name__ == "__main__":
    main()
