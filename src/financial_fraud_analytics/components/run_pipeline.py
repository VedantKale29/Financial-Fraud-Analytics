from financial_fraud_analytics.pipelines.training_pipeline import TrainingPipeline


if __name__ == "__main__":

    pipeline = TrainingPipeline()

    pipeline.run()

    print("Pipeline finished")