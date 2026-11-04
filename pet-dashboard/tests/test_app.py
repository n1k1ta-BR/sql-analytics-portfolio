"""Smoke tests for navigation, filters and empty sales periods."""
from datetime import date
from pathlib import Path
import sys
import unittest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class AppTests(unittest.TestCase):
    def test_pages_and_channels(self):
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        for page in ['Продажи', 'Пользователи', 'Возможности роста']:
            app.radio(key='page').set_value(page).run()
            for channel in ['organic', 'email', 'paid_ads', 'referral', 'all']:
                app.selectbox(key='channel').set_value(channel).run()
                self.assertEqual(len(app.exception), 0, (page, channel))
                self.assertGreaterEqual(len(app.metric), 3)

    def test_sales_dates_and_top_selection(self):
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
        options = app.selectbox(key='top_month').options
        app.selectbox(key='top_month').set_value(options[-1]).run()
        self.assertEqual(len(app.exception), 0)
        app.date_input(key='sales_dates').set_value((date(2024, 3, 1), date(2024, 3, 31))).run()
        self.assertEqual(len(app.exception), 0)
        # Find a day with no paid orders to exercise the empty state.
        import analytics
        conn = analytics.connect()
        try:
            bounds = analytics.metadata()
            candidate = None
            for d in __import__('pandas').date_range(bounds['start'], bounds['end']):
                if analytics.query(conn, '00_sales', start=str(d.date()), end=str(d.date())).iloc[0].paid_orders == 0:
                    candidate = d.date()
                    break
        finally:
            conn.close()
        self.assertIsNotNone(candidate)
        app.date_input(key='sales_dates').set_value((candidate, candidate)).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, '0,00')
        self.assertGreater(len(app.info), 0)


if __name__ == '__main__':
    unittest.main()
