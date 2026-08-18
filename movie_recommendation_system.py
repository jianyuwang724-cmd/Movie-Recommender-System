import re

import pandas as pd
from rapidfuzz import fuzz, process


class Movie_recommendation:

    def __init__(self, data_path: str):

        try:
            self.df = pd.read_csv(data_path)

            # Find the movie title column
            self.title_column = self.find_column(
                self.df,
                [
                    "title",
                    "movie_title",
                    "movie name",
                    "movie_name",
                    "name"
                ]
            )

            # Find the genre column
            self.genre_column = self.find_column(
                self.df,
                [
                    "genres",
                    "genre",
                    "category",
                    "categories"
                ]
            )

            if self.title_column is None:
                raise ValueError(
                    "Could not find a movie title column"
                )

            if self.genre_column is None:
                raise ValueError(
                    "Could not find a genre column"
                )

            # Parse genres
            self.df["genres_set"] = self.df[
                self.genre_column
            ].apply(self.parse_genres)

        except FileNotFoundError:
            print("File not found")


    @staticmethod
    def find_column(df, possible_columns):

        columns = {
            column.lower().strip(): column
            for column in df.columns
        }

        for name in possible_columns:
            if name in columns:
                return columns[name]

        return None


    @staticmethod
    def parse_genres(value):

        if pd.isna(value):
            return set()

        value = str(value)

        for separator in ["|", ",", ";", "/"]:

            if separator in value:
                return {
                    genre.strip().lower()
                    for genre in value.split(separator)
                    if genre.strip()
                }

        return {value.strip().lower()}


    @staticmethod
    def jaccard_similarity(
        set1: set,
        set2: set
    ) -> float:

        intersection = set1 & set2
        union = set1 | set2

        if len(union) == 0:
            return 0.0

        return len(intersection) / len(union)


    @staticmethod
    def _normalize_title(title) -> str:
        """Normalise a movie title so slight differences (case, year,
        punctuation) don't break matching."""

        if pd.isna(title):
            return ""

        value = str(title).lower()

        # Drop the release year, e.g. "Toy Story (1995)" -> "Toy Story"
        value = re.sub(r"\(\d{4}\)", " ", value)

        # Replace punctuation with spaces
        value = re.sub(r"[^a-z0-9\s]", " ", value)

        # Collapse whitespace
        value = re.sub(r"\s+", " ", value).strip()

        return value


    def find_movie(
        self,
        query: str,
        top_n: int = 3,
        score_cutoff: float = 80.0
    ) -> dict:
        """Resolve a user's typed input to a real movie title.

        Returns a dict with a "status" field:
          - "exact":     input matched a title exactly (case-insensitive)
          - "ambiguous": no exact match, "candidates" holds the closest
          - "not_found": nothing close enough found
        """

        query = str(query).strip()

        if not query:
            return {"status": "not_found"}

        titles = self.df[self.title_column].tolist()

        # 1) Exact match (case / surrounding whitespace insensitive)
        query_lower = query.lower()

        for title in titles:
            if str(title).strip().lower() == query_lower:
                return {"status": "exact", "title": title}

        # 2) No exact match -> fuzzy match the closest titles
        matches = process.extract(
            query,
            titles,
            processor=self._normalize_title,
            scorer=fuzz.WRatio,
            score_cutoff=score_cutoff,
            limit=top_n
        )

        if not matches:
            return {"status": "not_found"}

        candidates = [
            {"title": title, "score": round(float(score), 1)}
            for title, score, _ in matches
        ]

        return {
            "status": "ambiguous",
            "candidates": candidates
        }


    def film_recommender(
        self,
        movie_title: str
    ) -> dict:

        target_row = self.df[
            self.df[self.title_column] == movie_title
        ]

        if target_row.empty:
            return {
                "error": "No such film found"
            }

        set1 = target_row[
            "genres_set"
        ].values[0]

        self.df["similarity"] = self.df[
            "genres_set"
        ].apply(
            lambda x: self.jaccard_similarity(
                set1,
                x
            )
        )

        candidates = self.df[
            self.df[self.title_column] != movie_title
        ]

        if candidates.empty:
            return {
                "error": "No other films to compare"
            }

        # Only keep movies that share at least one genre (similarity > 0)
        candidates = candidates[candidates["similarity"] > 0]

        if candidates.empty:
            return {
                "error": "No similar film found"
            }

        best_matches = candidates.sort_values(
            by="similarity",
            ascending=False
        ).head(5)

        recommendations = [
            {
                "title": title,
                "similarity": round(float(sim), 4)
            }
            for title, sim in zip(
                best_matches[self.title_column].tolist(),
                best_matches["similarity"].tolist()
            )
        ]

        return {
            "Recommendations": recommendations
        }


if __name__ == "__main__":

    recommender = Movie_recommendation(
        "data/movies_test.csv"
    )

    query = input(
        "Please enter your favourite film: "
    ).strip()

    while True:

        result = recommender.find_movie(query)

        if result["status"] == "exact":
            film_name = result["title"]
            break

        if result["status"] == "ambiguous":

            candidates = result["candidates"]
            guess = candidates[0]["title"]

            answer = input(
                f"Did you mean '{guess}'? (y/n): "
            ).strip().lower()

            if answer in ("y", "yes"):
                film_name = guess
                break

            # Offer the rest of the candidates to pick from
            if len(candidates) > 1:
                print("Other close matches:")
                for i, candidate in enumerate(candidates, start=1):
                    print(f"  {i}. {candidate['title']}")

                choice = input(
                    "Enter a number to select, or type a new name: "
                ).strip()

                if choice.isdigit() and 1 <= int(choice) <= len(candidates):
                    film_name = candidates[int(choice) - 1]["title"]
                    break

                query = choice
                continue

            query = input(
                "Please re-enter the film name: "
            ).strip()
            continue

        # not_found
        query = input(
            "No matching film found. Please re-enter the film name: "
        ).strip()

    print(recommender.film_recommender(film_name))
