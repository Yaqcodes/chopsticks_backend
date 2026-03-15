#!/usr/bin/env python3
"""
Copy ZMall tenant (id=4) and all associated categories, menu items, and
menu item images from 'db before migration fix.sqlite3' to chopsticks_backend/db.sqlite3.
"""
import sqlite3
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SOURCE_DB = os.path.join(os.path.dirname(BASE), "db before migration fix.sqlite3")
TARGET_DB = os.path.join(BASE, "db.sqlite3")
ZMALL_SOURCE_ID = 4


def main():
    if not os.path.exists(SOURCE_DB):
        print(f"Source DB not found: {SOURCE_DB}")
        return 1
    if not os.path.exists(TARGET_DB):
        print(f"Target DB not found: {TARGET_DB}")
        return 1

    src = sqlite3.connect(SOURCE_DB)
    src.row_factory = sqlite3.Row
    tgt = sqlite3.connect(TARGET_DB)

    try:
        # 1) Copy tenant (core_restaurantsettings id=4)
        row = src.execute(
            "SELECT * FROM core_restaurantsettings WHERE id = ?", (ZMALL_SOURCE_ID,)
        ).fetchone()
        if not row:
            print("ZMall tenant (id=4) not found in source.")
            return 1

        keys = [k for k in row.keys() if k != "id"]
        placeholders = ",".join("?" * len(keys))
        cols = ",".join(keys)
        tgt.execute(
            f"INSERT INTO core_restaurantsettings ({cols}) VALUES ({placeholders})",
            [row[k] for k in keys],
        )
        new_tenant_id = tgt.execute("SELECT last_insert_rowid()").fetchone()[0]
        print(f"Inserted tenant ZMall -> new id = {new_tenant_id}")

        # 2) Copy categories (restaurant_settings_id=4 -> new_tenant_id)
        cat_rows = src.execute(
            "SELECT * FROM menu_category WHERE restaurant_settings_id = ? ORDER BY id",
            (ZMALL_SOURCE_ID,),
        ).fetchall()
        cat_map = {}  # old_category_id -> new_category_id
        for r in cat_rows:
            keys = [k for k in r.keys() if k != "id"]
            vals = [r[k] if k != "restaurant_settings_id" else new_tenant_id for k in keys]
            placeholders = ",".join("?" * len(keys))
            cols = ",".join(keys)
            tgt.execute(f"INSERT INTO menu_category ({cols}) VALUES ({placeholders})", vals)
            new_cat_id = tgt.execute("SELECT last_insert_rowid()").fetchone()[0]
            cat_map[r["id"]] = new_cat_id
        print(f"Inserted {len(cat_map)} categories.")

        # 3) Copy menu items
        mi_rows = src.execute(
            "SELECT * FROM menu_menuitem WHERE restaurant_settings_id = ? ORDER BY id",
            (ZMALL_SOURCE_ID,),
        ).fetchall()
        mi_map = {}  # old_menuitem_id -> new_menuitem_id
        for r in mi_rows:
            keys = [k for k in r.keys() if k != "id"]
            vals = []
            for k in keys:
                if k == "restaurant_settings_id":
                    vals.append(new_tenant_id)
                elif k == "category_id":
                    vals.append(cat_map[r[k]])
                else:
                    vals.append(r[k])
            placeholders = ",".join("?" * len(keys))
            cols = ",".join(keys)
            tgt.execute(f"INSERT INTO menu_menuitem ({cols}) VALUES ({placeholders})", vals)
            new_mi_id = tgt.execute("SELECT last_insert_rowid()").fetchone()[0]
            mi_map[r["id"]] = new_mi_id
        print(f"Inserted {len(mi_map)} menu items.")

        # 4) Copy menu item images (only for menu items we just copied)
        img_rows = src.execute(
            """SELECT mi.* FROM menu_menuitemimage mi
               JOIN menu_menuitem m ON mi.menu_item_id = m.id
               WHERE m.restaurant_settings_id = ? ORDER BY mi.id""",
            (ZMALL_SOURCE_ID,),
        ).fetchall()
        for r in img_rows:
            old_mi_id = r["menu_item_id"]
            if old_mi_id not in mi_map:
                continue
            keys = [k for k in r.keys() if k != "id"]
            vals = [r[k] if k != "menu_item_id" else mi_map[old_mi_id] for k in keys]
            placeholders = ",".join("?" * len(keys))
            cols = ",".join(keys)
            tgt.execute(
                f"INSERT INTO menu_menuitemimage ({cols}) VALUES ({placeholders})", vals
            )
        print(f"Inserted {len(img_rows)} menu item images.")

        tgt.commit()
        print("Done. ZMall tenant and related data copied to chopsticks_backend/db.sqlite3")
        return 0
    finally:
        src.close()
        tgt.close()


if __name__ == "__main__":
    exit(main())
