from datasets import load_dataset
from loguru import logger
from trl import SFTTrainer

from utils import *


def main():
    args = parse_arguments()

    cfg = get_config(f"{args.model}")

    model_cfg = cfg.model
    dataset_cfg = cfg.dataset
    train_cfg = cfg.training_arguments

    output_dir = setup_output_directory(train_cfg, model_cfg, dataset_cfg)

    logger.info(f"Model ID: {model_cfg.id}")
    logger.info(f"Dataset ID: {dataset_cfg.id}")
    logger.info(f"Output Directory: {output_dir}")
    logger.info(f"Training Epochs: {train_cfg.epochs}")

    dataset = load_dataset(dataset_cfg.id)
    train_dataset, eval_dataset = prepare_datasets(
        dataset, dataset_cfg.instruction_column_name, dataset_cfg.response_column_name
    )

    logger.info(f"Training Dataset: {len(train_dataset)} examples")
    logger.info(f"Evaluation Dataset: {len(eval_dataset)} examples")

    tokenizer = load_tokenizer(model_cfg)

    device, quantization_config = setup_device_and_quantization(cfg.model)

    model = load_model(cfg.model, quantization_config, device)

    example1 = eval_dataset[0]
    response = generate_response(model, tokenizer, example1["instruction"], device)

    print_example(example1)
    print_response(response)

    peft_config = create_peft_config(cfg.model)
    sft_config = create_sft_config(cfg.training_arguments, output_dir)

    formatting_func = lambda example: formatting_prompts_func(example, tokenizer)
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        formatting_func=formatting_func,
        peft_config=peft_config,
        args=sft_config,
    )
    trainer.train()
    trainer.evaluate()
    trainer.save_model()

    if cfg.hugging_face.push_to_hub and (token := cfg.hugging_face.token):
        trainer.push_to_hub(token=token)

    ft_model = AutoModelForCausalLM.from_pretrained(output_dir).to(device)
    response = generate_response(ft_model, tokenizer, example1["instruction"], device)

    print_example(example1)
    print_response(response)


if __name__ == "__main__":
    main()
