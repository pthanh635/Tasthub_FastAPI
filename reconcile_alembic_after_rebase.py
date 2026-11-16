#!/usr/bin/env python3
"""Reconcile Day-2 and Day-3 Alembic revision ancestry after Git rebase.
Only use after Day-2 review migration is already present in the rebased tree.
Review and back up the database separately before migrating.
"""
from pathlib import Path

root = Path.cwd()
day2 = root / 'alembic/versions/0002_day2_review_fixes.py'
auth = root / 'alembic/versions/0002_auth_and_rbac.py'
review = root / 'alembic/versions/0003_pm_review_fixes.py'
if not all(p.exists() for p in (day2,auth,review)):
    raise SystemExit('Required Alembic files missing. Did you finish the Day-3 rebase?')
a=auth.read_text('utf-8')
a0=a
old='down_revision: str | Sequence[str] | None = "0001_initial_schema"'
new='down_revision: str | Sequence[str] | None = "0002_day2_review_fixes"'
if old in a:
    a=a.replace(old,new)
elif new not in a:
    raise SystemExit('Unexpected auth migration ancestry; no files changed.')
r=review.read_text('utf-8')
r0=r
for line in [
 '    ("comments", "task_id", "tasks", "CASCADE"),\n',
 '    ("task_labels", "task_id", "tasks", "CASCADE"),\n',
 '    op.create_index("ix_task_labels_label_id", "task_labels", ["label_id"])\n',
 '    op.drop_index("ix_task_labels_label_id", table_name="task_labels")\n',
]:
    if line in r:
        r=r.replace(line,'')
if 'FOREIGN_KEYS = (' not in r:
    raise SystemExit('Unknown review migration structure; no files changed.')
if a==a0 and r==r0:
    print('Already reconciled, no files changed.')
else:
    auth.write_text(a,'utf-8')
    review.write_text(r,'utf-8')
    print('Reconciled: 0001 -> 0002_day2_review_fixes -> 0002_auth_and_rbac -> 0003_pm_review_fixes')
    print('Review git diff and run python -m alembic history before any database upgrade.')
