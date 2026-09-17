import unittest
from datetime import date
from decimal import Decimal

from flask import template_rendered

from app import create_app, db
from app.models import Gasto, Rol, TipoGasto, Usuario, VentaDiaria


class TestConfig:
    TESTING = True
    SECRET_KEY = 'test'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False


class InformeMensualTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        user = Usuario(username='test', email='test@example.com',
                       nombre_completo='Test', password_hash='test',
                       rol=Rol(nombre='Administrador'))
        db.session.add(user)
        db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
        self.rendered = []
        template_rendered.connect(self.capture, self.app)

    def capture(self, sender, template, context, **extra):
        self.rendered.append(context)

    def tearDown(self):
        template_rendered.disconnect(self.capture, self.app)
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def report(self, extra=''):
        response = self.client.get('/reportes/mensual?mes=9&anio=2026' + extra)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Informe Mensual', response.get_data(as_text=True))
        return self.rendered[-1], response.get_data(as_text=True)

    def add_sales(self):
        db.session.add(VentaDiaria(fecha=date(2026, 9, 7),
                                  estado='cerrado_definitivo', total_ventas=1000))
        db.session.commit()

    def test_sales_without_fixed_costs(self):
        self.add_sales()
        context, html = self.report()
        self.assertEqual(context['ventas_objetivo'], 0)
        self.assertIsNone(context['cobertura_objetivo_pct'])
        self.assertEqual(context['venta_diaria_objetivo'], 0)
        self.assertEqual(context['diferencia_promedio_diario'], 1000)
        self.assertIn('Sin costos fijos registrados', html)

    def test_empty_month(self):
        context, html = self.report()
        self.assertEqual(context['total_ventas'], 0)
        self.assertIsNone(context['ventas_objetivo'])

    def test_regular_target(self):
        self.add_sales()
        db.session.add(Gasto(fecha=date(2026, 9, 7), descripcion='Servicio',
                            monto=200, tipo_gasto=TipoGasto(nombre='Servicios')))
        db.session.commit()
        context, html = self.report('&utilidad_objetivo=20')
        self.assertEqual(context['ventas_objetivo'], Decimal('250'))
        self.assertEqual(context['cobertura_objetivo_pct'], Decimal('400'))
        self.assertEqual(context['venta_diaria_objetivo'], Decimal('250'))


if __name__ == '__main__':
    unittest.main()
