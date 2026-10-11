import sys
from h import session
with session(1440, 1000) as (pg, errs):
    print('title:', pg.title())
    pg.screenshot(path='shots_open.png')
    print('errs', [e for e in errs if 'fonts' not in e][:10])
    print(pg.inner_text('body')[:600])
