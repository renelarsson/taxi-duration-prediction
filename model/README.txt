This directory should contain a valid model.pkl file for integration tests.

The model.pkl is a pickled scikit-learn model artifact. 
After training your model (saved in the 'models/' directory by the training pipeline), 
copy the trained model.pkl here:

    cp models/model.pkl integration-test/model/model.pkl

If this file is empty or missing, integration tests will not work.
This file is just a placeholder in the course repo.