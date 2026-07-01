import pandas as pd


class Movie_recommendation:
    # initialize the system
    def __init__(self,data_path: str):
        try:
            self.df = pd.read_csv(data_path)
            self.df["genres_list"] = self.df["genres"].str.split("|")
            self.df["genres_set"] = self.df["genres_list"].apply(set)
        except FileNotFoundError:
            print ("File not found")



    # The main function for calculating similarity
    @staticmethod
    def jaccard_similarity(set1:set,set2:set) -> float:
        intersection = set1 & set2
        union = set1 | set2
        if len(union) == 0:
          return 0.0
        else:
          jaccard_similarity = len(intersection) / len(union)
        return jaccard_similarity
    
    def film_recommender(self, movie_title: str) -> dict:
        target_row = self.df[self.df["title"] == movie_title]
        if target_row.empty:
            return {"error":"No such film found"}
        else:
            set1 = target_row["genres_set"].values[0]
            self.df["similarity"] = self.df["genres_set"].apply(
                lambda x: self.jaccard_similarity(set1, x)
            )

            candidates = self.df[self.df["title"] != movie_title]
            if candidates.empty:
                return {"error": "no other films to compare"}
            else:
                max_sim = candidates["similarity"].max()
                if max_sim == 0:
                    return {"error": "no such film found"}
                else:
                    best_matches = candidates.sort_values(by="similarity", ascending=False).head(5)["title"].tolist() 
                    return {"Recommendations": best_matches,
                            "Similarity": float(max_sim)
                            }       


if __name__ == "__main__":
    recommender  = Movie_recommendation("data/movies.csv")        
    film_name = input("Please enter your favourate film: ")
    result = recommender.film_recommender(film_name)
    print(result)

    
