# -*- coding: utf-8 -*-
"""
🧪 Moon Club｜成就盲盒開發測試版

用途：
1. 測試成就完成後是否取得盲盒資格
2. 測試不同成就等級的盲盒
3. 測試抽獎後資格是否正確扣除
4. 模擬大量抽獎，檢查各等級機率

這個檔案只供測試，不需要接進 main.py。
"""

from moon_achievements import (
    AchievementStore,
    AchievementEngine,
    ACHIEVEMENTS,
    EASY,
    MEDIUM,
    MEDIUM_HIGH,
    HIGH,
    LOOT_WEIGHTS,
    roll_loot,
)

import sqlite3
from collections import Counter


TEST_USER_ID = 999999999


def show_achievements():
    print("\n" + "=" * 55)
    print("🏆 Moon Club｜80 個成就")
    print("=" * 55)

    groups = [
        ("🟢 簡單", EASY),
        ("🟡 中", MEDIUM),
        ("🟠 中高", MEDIUM_HIGH),
        ("🔴 高", HIGH),
    ]

    for title, difficulty in groups:
        print(f"\n{title}")
        for a in ACHIEVEMENTS:
            if a.difficulty == difficulty:
                print(f"{a.achievement_id}｜{a.name}")
                print(f"   └─ {a.description}")


def show_status(store):
    count = store.get_draw_count(TEST_USER_ID)

    completed = []
    for a in ACHIEVEMENTS:
        row = store.db.execute(
            """
            SELECT completed
            FROM moon_achievements
            WHERE user_id = ? AND achievement_id = ?
            """,
            (TEST_USER_ID, a.achievement_id),
        ).fetchone()

        if row and row[0]:
            completed.append(a)

    print("\n" + "=" * 55)
    print("📊 測試玩家狀態")
    print("=" * 55)
    print(f"已完成成就：{len(completed)} / {len(ACHIEVEMENTS)}")
    print(f"🎟️ 成就盲盒資格：{count} 次")

    if completed:
        print("\n已完成：")
        for a in completed:
            print(f"  • {a.achievement_id}｜{a.name}｜{a.difficulty}")


def add_test_draws(store, difficulty, count=1):
    """開發測試用：直接建立指定難度的盲盒資格。"""
    if count <= 0:
        print("❌ 次數必須大於 0。")
        return

    for _ in range(count):
        store.add_draw_qualification(TEST_USER_ID, difficulty)

    print(f"🎟️ 已加入 {count} 次「{difficulty}」盲盒資格。")


def complete_test_achievement(store, achievement_id):
    achievement = next(
        (a for a in ACHIEVEMENTS if a.achievement_id == achievement_id),
        None,
    )

    if achievement is None:
        print("❌ 找不到這個成就。")
        return

    first_time = store.complete_achievement(
        TEST_USER_ID,
        achievement_id,
    )

    if first_time:
        print(f"\n🏆 成就完成！")
        print(f"{achievement.name}")
        print(f"難度：{achievement.difficulty}")
        print("🎁 成就盲盒資格 +1")
    else:
        print("\n⚠️ 這個成就之前已完成。")
        print("不會再次增加盲盒資格。")


def draw_box(store):
    count = store.get_draw_count(TEST_USER_ID)

    if count <= 0:
        print("\n❌ 目前沒有成就盲盒資格。")
        print("請先完成測試成就。")
        return

    print("\n選擇本次盲盒要模擬哪個成就等級：")
    print("1️⃣ 簡單")
    print("2️⃣ 中")
    print("3️⃣ 中高")
    print("4️⃣ 高")

    choice = input("請輸入：").strip()

    difficulty_map = {
        "1": EASY,
        "2": MEDIUM,
        "3": MEDIUM_HIGH,
        "4": HIGH,
    }

    difficulty = difficulty_map.get(choice)

    if difficulty is None:
        print("❌ 選項錯誤。")
        return

    reward = store.draw_box(TEST_USER_ID, difficulty)

    if reward is None:
        print("❌ 抽獎失敗：沒有剩餘資格。")
        return

    print("\n" + "🎁" * 10)
    print("       成就盲盒開啟！")
    print("🎁" * 10)
    print(f"\n✨ 獲得：{reward}")
    print(f"剩餘盲盒資格：{store.get_draw_count(TEST_USER_ID)}")


def show_probabilities():
    print("\n" + "=" * 55)
    print("🎲 成就盲盒｜目前機率")
    print("=" * 55)

    for difficulty, weights in LOOT_WEIGHTS.items():
        total = sum(weights.values())

        print(f"\n【{difficulty}】")
        for reward, weight in weights.items():
            percentage = weight / total * 100
            print(f"{reward:<18} {percentage:>5.1f}%")


def simulate():
    print("\n" + "=" * 55)
    print("🧪 大量抽獎機率模擬")
    print("=" * 55)

    raw = input("要模擬幾次？（例如 1000）：").strip()

    try:
        times = int(raw)
        if times <= 0:
            raise ValueError
    except ValueError:
        print("❌ 請輸入正整數。")
        return

    print("\n選擇等級：")
    print("1️⃣ 簡單")
    print("2️⃣ 中")
    print("3️⃣ 中高")
    print("4️⃣ 高")

    choice = input("請輸入：").strip()

    difficulty_map = {
        "1": EASY,
        "2": MEDIUM,
        "3": MEDIUM_HIGH,
        "4": HIGH,
    }

    difficulty = difficulty_map.get(choice)

    if difficulty is None:
        print("❌ 選項錯誤。")
        return

    results = Counter(
        roll_loot(difficulty)
        for _ in range(times)
    )

    print(f"\n📊 {difficulty}｜模擬 {times:,} 次")
    print("-" * 55)

    for reward, weight in LOOT_WEIGHTS[difficulty].items():
        actual = results[reward] / times * 100
        expected = weight / sum(LOOT_WEIGHTS[difficulty].values()) * 100

        print(
            f"{reward:<18}"
            f"預期 {expected:>5.1f}%  "
            f"實際 {actual:>5.1f}%"
        )


def reset_test_data(store):
    store.db.execute(
        "DELETE FROM moon_achievements WHERE user_id = ?",
        (TEST_USER_ID,),
    )
    store.db.execute(
        "DELETE FROM moon_achievement_loot WHERE user_id = ?",
        (TEST_USER_ID,),
    )
    store.db.commit()

    print("\n🗑️ 測試資料已清除。")


def main():
    db = sqlite3.connect(":memory:")
    store = AchievementStore(db)
    AchievementEngine(store)

    print("\n🌙 Moon Club｜成就盲盒測試器")
    print("⚠️ 這是獨立開發測試，不會修改正式資料；可快速建立指定難度資格。")

    while True:
        print("\n" + "=" * 55)
        print("🧪 測試選單")
        print("=" * 55)
        print("1️⃣ 查看 80 個成就")
        print("2️⃣ 完成測試成就")
        print("3️⃣ 查看目前資格／完成狀態")
        print("4️⃣ 開啟成就盲盒")
        print("5️⃣ 查看目前盲盒機率")
        print("6️⃣ 模擬大量抽獎")
        print("7️⃣ 清除測試資料")
        print("8️⃣ 快速建立測試資格")
        print("0️⃣ 離開")

        choice = input("\n請選擇：").strip()

        if choice == "1":
            show_achievements()

        elif choice == "2":
            achievement_id = input(
                "\n輸入要完成的成就 ID（例如 ACH_001）："
            ).strip().upper()

            complete_test_achievement(
                store,
                achievement_id,
            )

        elif choice == "3":
            show_status(store)

        elif choice == "4":
            draw_box(store)

        elif choice == "5":
            show_probabilities()

        elif choice == "6":
            simulate()

        elif choice == "7":
            reset_test_data(store)

        elif choice == "8":
            print("\n選擇要快速建立的盲盒等級：")
            print("1️⃣ 簡單")
            print("2️⃣ 中")
            print("3️⃣ 中高")
            print("4️⃣ 高")

            difficulty_map = {
                "1": EASY,
                "2": MEDIUM,
                "3": MEDIUM_HIGH,
                "4": HIGH,
            }

            d_choice = input("請輸入：").strip()
            difficulty = difficulty_map.get(d_choice)

            if difficulty is None:
                print("❌ 選項錯誤。")
                continue

            raw_count = input("要建立幾次資格？（例如 5）：").strip()
            try:
                count = int(raw_count)
            except ValueError:
                print("❌ 請輸入正整數。")
                continue

            add_test_draws(store, difficulty, count)

        elif choice == "0":
            print("\n🌙 測試結束。")
            break

        else:
            print("\n❌ 無效選項。")


if __name__ == "__main__":
    main()
