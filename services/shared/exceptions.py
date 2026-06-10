"""Domain exceptions raised by shared database operations."""


class CatalogMovieAlreadyExists(Exception):
    """
    Raised when a catalog movie insert targets a movie_id that already exists.

    ============================ Arguments ============================
    movie_id: The movie_id that already exists in catalog_movies.
    """

    def __init__(self, movie_id: int) -> None:
        self.movie_id = movie_id
        super().__init__(f"Movie with movie_id={movie_id} already exists")
