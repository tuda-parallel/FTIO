# Machine-Learning Models Documentation

## General Usage
[Hybrid Model]

The following example shows the high-level entry to training and forecasting using the function train_hybrid_model() of the hybrid-model.
```python
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    model = train_hybrid_model(file, epochs=10, lr=0.003)
    prediction = predict_next_sequence(model, file)
```
The function train_hybrid_model() also has parameters with standard values for the underlying structure of the model which can be changed.
In this example only the embedded dimension is changed, but there are also parameters for the attention heads, the feed-forward dimension etc.
Common values such as 2^n are usually the most effective variations to explore. 
```python
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    model = train_hybrid_model(file, epochs=10, lr=0.003, emb_dim = 256)
    prediction = predict_next_sequence(model, file)
```
The training of the hybrid-model can be resumed by loading a .pth file created by the saving process.
It contains the parameters of the model and the state of the used optimizer. 
```python
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    model = train_hybrid_model(file, epochs=10, lr=0.003, save=True)
    model = train_hybrid_model(
        file,
        epochs=10,
        lr=0.003,
        load_state_dict_and_optimizer_state="model_and_optimizer.pth",
    )
    prediction = predict_next_sequence(model, file)
```
[(S)ARIMA]

The following example shows the high-level entry to training and forecasting using the train_arima() function of the ARIMA/SARIMA models.
By changing the model_architecture parameter SARIMA or ARIMA can be selected. The max_depth is recommended to be relatively small, 
since it's defining the maximum depth of differentations of the underlying data to reach stationarity.
A resumption of training is inherently not supported by the underlying model structure. Therefore, if new data is available, then 
training from the beginning is the only option.
```python
    file = os.path.join(os.path.dirname(__file__), "../examples/tmio/JSONL/8.jsonl")
    prediction = train_arima(file, max_depth = 3, model_architecture="ARIMA")
```
