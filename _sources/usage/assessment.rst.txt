Assessment and Review Management
============================

This guide covers how to use referia's assessment and review management capabilities.

Overview
-------

Referia extends lynguine's core functionality with specific features for managing review processes:

- Handling review submissions
- Processing reviewer feedback
- Scoring reviews against criteria
- Generating summaries and reports

The Review Class
-------------

The main entry point for review management is the ``Review`` class:

.. code-block:: python

    from referia.assess.review import Review
    from referia.config.interface import Interface
    
    # Load review configuration
    interface = Interface.from_file("review_process.yml")
    
    # Create a review manager
    review = Review(interface)
    
    # Process review submissions
    review.process_submissions()
    
    # Generate summaries
    summaries = review.generate_summaries()

Configuration for Review Processes
-------------------------------

A typical review configuration might include:

.. code-block:: yaml

    # Basic configuration
    input:
      type: file
      file: submissions.csv
      index: id
    
    # Review-specific configuration
    review:
      criteria:
        - name: clarity
          weight: 0.3
          description: "How clear is the submission?"
        - name: methodology
          weight: 0.4
          description: "How sound is the methodology?"
        - name: impact
          weight: 0.3
          description: "What is the potential impact?"
      
      scoring:
        scale: 1-5
        passing_threshold: 3.0
    
    # Computation steps
    compute:
      compute:
        - function: word_count
          field: word_count
          args:
            column: review_text
        
        - function: text_summarizer
          field: summary
          args:
            column: review_text
            max_length: 200

Managing Review Data
-----------------

Referia uses lynguine's ``CustomDataFrame`` for data management but adds review-specific functionality:

.. code-block:: python

    from lynguine.assess.data import CustomDataFrame
    from referia.assess.review import process_reviews
    
    # Load submission data
    submissions = CustomDataFrame.from_csv("submissions.csv")
    
    # Load reviewer data
    reviewers = CustomDataFrame.from_csv("reviewers.csv")
    
    # Process reviews
    reviews = process_reviews(submissions, reviewers, interface)
    
    # Calculate scores
    scores = calculate_scores(reviews, interface["review"]["criteria"])

Scoring and Assessment
-------------------

Referia provides functions for scoring reviews against defined criteria:

.. code-block:: python

    from referia.assess.review import score_reviews
    
    # Score reviews against criteria
    scores = score_reviews(reviews, criteria=interface["review"]["criteria"])
    
    # Calculate overall scores
    overall_scores = calculate_overall_scores(scores)
    
    # Determine acceptance based on threshold
    acceptance = overall_scores >= interface["review"]["scoring"]["passing_threshold"]

Generating Reports
---------------

Referia can generate various reports from review data:

.. code-block:: python

    from referia.assess.review import generate_summary_report
    
    # Generate summary report
    report = generate_summary_report(reviews, scores, interface)
    
    # Export report to file
    report.to_csv("review_summary.csv")
    
    # Generate detailed feedback for authors
    feedback = generate_author_feedback(reviews, scores, interface)

Integration with Compute Framework
-------------------------------

The review functionality integrates with referia's compute framework (which inherits from lynguine):

.. code-block:: python

    from referia.assess.compute import Compute
    from referia.assess.review import Review
    
    # Create compute object
    compute = Compute(interface)
    
    # Create review object
    review = Review(interface)
    
    # Run computations on review data
    compute.run_all(review.data, interface)
    
    # Use computed results in review processing
    review.process_with_computed_data()

Workflow Example
-------------

A complete review management workflow might look like:

1. **Configuration**: Define review criteria and process
2. **Data Collection**: Gather submissions and reviewer information
3. **Review Assignment**: Assign reviewers to submissions
4. **Review Processing**: Process review feedback
5. **Scoring**: Score reviews against criteria
6. **Reporting**: Generate reports and feedback
7. **Decision**: Make decisions based on review scores

.. code-block:: python

    # Complete workflow example
    
    # 1. Load configuration
    interface = Interface.from_file("review_process.yml")
    
    # 2. Create review manager
    review = Review(interface)
    
    # 3. Load submission data
    review.load_submissions("submissions.csv")
    
    # 4. Load reviewer data
    review.load_reviewers("reviewers.csv")
    
    # 5. Assign reviewers to submissions
    review.assign_reviewers(method="balanced")
    
    # 6. Process reviews
    review.process_reviews()
    
    # 7. Calculate scores
    scores = review.calculate_scores()
    
    # 8. Generate reports
    summary = review.generate_summary()
    feedback = review.generate_feedback()
    
    # 9. Export results
    review.export_results("review_results.csv") 