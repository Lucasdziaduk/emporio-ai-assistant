from app.data.database import create_connection
from app.data.loader import load_dataset
from app.data.repositories import (
    CategoryRepository,
    CustomerRepository,
    OrderRepository,
    ProductRepository,
    PromotionRepository,
)
from tests.fixtures.dataset_factory import write_dataset


def test_repositories_map_rows_to_domain_models(tmp_path):
    source = write_dataset(tmp_path / "source")
    connection = create_connection()
    load_dataset(source, connection)

    assert CategoryRepository(connection).get_by_id(1).name == "Violões"
    assert ProductRepository(connection).get_by_id(81).name == "Violão de teste"
    assert PromotionRepository(connection).list_active_for_product(81)[0].discount_percent == 10
    assert CustomerRepository(connection).get_by_id(1).name == "Cliente Um"
    assert OrderRepository(connection).get_customer_id(1) == 1

    assert ProductRepository(connection).get_by_id(999) is None
    assert OrderRepository(connection).get_by_id(999) is None
    connection.close()
