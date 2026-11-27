"""RoomClimate v0.1 — estimativa estacionária de carga térmica (SI).
Python 3.10+, sem dependências externas. Execute: python roomclimate.py
Temperaturas em °C, potências em W, razão de umidade em kg/kg de ar seco.
"""
from dataclasses import dataclass, replace
from math import isclose

W_TO_BTUH = 3.412141633
RHO_AIR = 1.2  # kg de ar seco/m³, aproximação
CP_AIR = 1006.0  # J/(kg K)
H_FG = 2.501e6  # J/kg, aproximação


@dataclass(frozen=True)
class Room:
    width: float = 3.0  # parede da janela
    length: float = 4.0
    height: float = 2.9
    window_area: float = 5.0

    def __post_init__(self):
        if min(self.width, self.length, self.height) <= 0:
            raise ValueError('Dimensões devem ser positivas.')
        if not 0 <= self.window_area <= self.width * self.height:
            raise ValueError('Área da janela incompatível com a fachada.')

    @property
    def floor_area(self):
        return self.width * self.length

    @property
    def volume(self):
        return self.floor_area * self.height

    @property
    def facade_area(self):
        return self.width * self.height - self.window_area

    @property
    def partition_area(self):
        # Inclui a porta com transmitância efetiva das divisórias.
        return (2 * self.length + self.width) * self.height


@dataclass(frozen=True)
class Scenario:
    name: str
    t_out: float
    t_adj: float
    t_roof_sol: float
    t_wall_sol: float
    t_floor_adj: float
    irradiance: float  # W/m² no plano da janela
    solar_factor: float  # vidro + persiana
    u_roof: float
    u_partition: float
    ach: float  # renovações de ar por hora
    w_out: float
    internal_sensible: float
    internal_latent: float = 55.0
    t_set: float = 21.0
    w_set: float = 0.0093  # aproximadamente 60% UR a 21 °C
    u_glass: float = 5.7  # todos os U em W/(m² K)
    u_wall: float = 2.0
    u_floor: float = 1.5


def thermal_load(room: Room, s: Scenario) -> dict[str, float]:
    """Fluxos sensíveis com sinal; carga latente positiva para desumidificar.
    Não calcula condensação nas superfícies nem desempenho do equipamento.
    """
    if not 0 <= s.solar_factor <= 1:
        raise ValueError('Fator solar fora de [0, 1].')
    if min(s.irradiance, s.ach, s.w_out, s.w_set, s.u_roof,
           s.u_partition, s.u_glass, s.u_wall, s.u_floor,
           s.internal_sensible, s.internal_latent) < 0:
        raise ValueError('Parâmetros físicos devem ser não negativos.')
    t = s.t_set
    m_dot = RHO_AIR * room.volume * s.ach / 3600
    q = {
        'solar': room.window_area * s.solar_factor * s.irradiance,
        'roof': s.u_roof * room.floor_area * (s.t_roof_sol - t),
        'glass': s.u_glass * room.window_area * (s.t_out - t),
        'partitions': s.u_partition * room.partition_area * (s.t_adj - t),
        'facade': s.u_wall * room.facade_area * (s.t_wall_sol - t),
        'floor': s.u_floor * room.floor_area * (s.t_floor_adj - t),
        'infiltration_sensible': m_dot * CP_AIR * (s.t_out - t),
        'internal_sensible': s.internal_sensible,
    }
    q['sensible'] = max(0.0, sum(q.values()))
    # Ar externo mais seco pode compensar parte da geração interna de vapor.
    q['infiltration_latent'] = m_dot * H_FG * (s.w_out - s.w_set)
    q['internal_latent'] = s.internal_latent
    q['latent'] = max(0.0, q['infiltration_latent'] + q['internal_latent'])
    q['total'] = q['sensible'] + q['latent']
    return q


def nominal_screening(total_w: float, margin: float = 0.10):
    """Triagem por capacidade total nominal, não seleção final de equipamento."""
    if total_w < 0 or margin < 0:
        raise ValueError('Carga e margem devem ser não negativas.')
    required = total_w * (1 + margin) * W_TO_BTUH
    candidate = next((c for c in (7500, 9000, 12000, 18000, 24000, 30000, 36000)
                      if c >= required), None)
    return required, candidate


SCENARIOS = (
    Scenario('Favorável', 33, 28, 42, 35, 25, 450, .35, .8, 1.3, .5, .017, 445),
    Scenario('Intermediário', 35, 30, 48, 41, 28, 600, .45, 2, 1.6, .75, .019, 545),
    Scenario('Desfavorável', 37, 32, 55, 46, 30, 750, .55, 3.5, 2, 1, .021, 695),
)


def self_test():
    room = Room()
    assert isclose(room.volume, 34.8)
    assert isclose(room.partition_area, 31.9)
    s = SCENARIOS[1]
    q = thermal_load(room, s)
    assert isclose(q['solar'], 1350)
    assert isclose(q['roof'], 648)
    assert isclose(q['glass'], 399)
    assert isclose(q['total'], q['sensible'] + q['latent'])
    zero = replace(s, t_out=21, t_adj=21, t_roof_sol=21,
                   t_wall_sol=21, t_floor_adj=21, irradiance=0,
                   w_out=s.w_set, internal_sensible=0, internal_latent=0)
    assert isclose(thermal_load(room, zero)['total'], 0)
    assert thermal_load(room, replace(s, t_set=20))['total'] > q['total']
    assert thermal_load(room, replace(s, u_roof=0))['total'] < q['total']
    assert thermal_load(room, replace(s, solar_factor=0))['solar'] == 0
    assert nominal_screening(q['total'])[1] == 18000


def main():
    self_test()
    room = Room()
    print('Testes básicos: OK')
    print(f'{"Cenário":15s} {"Sens. W":>9s} {"Lat. W":>9s} {"Total W":>9s} '
          f'{"BTU/h +10%":>12s} {"Candidato":>10s}')
    for s in SCENARIOS:
        q = thermal_load(room, s)
        req, candidate = nominal_screening(q['total'])
        print(f'{s.name:15s} {q["sensible"]:9.1f} {q["latent"]:9.1f} '
              f'{q["total"]:9.1f} {req:12.0f} {str(candidate):>10s}')


if __name__ == '__main__':
    main()
