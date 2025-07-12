# test.py
import os
import sys
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoConfig
import logging
import traceback

# Setup logging với format chi tiết
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# Lấy thông tin file hiện tại
current_file = Path(__file__).name
current_dir = Path(__file__).parent.absolute()
logger.info(f"🔍 Đang chạy file: {current_file}")
logger.info(f"📁 Thư mục hiện tại: {current_dir}")

# Add project root to path
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))
logger.info(f"🔗 Thêm vào sys.path: {project_root}")

# Kiểm tra các file cần thiết
required_files = [
    current_dir / "vphoberttagger" / "models.py",
    current_dir / "vphoberttagger" / "constant.py", 
    current_dir / "vphoberttagger" / "helper.py"
]

for file_path in required_files:
    if file_path.exists():
        logger.info(f"✅ Tìm thấy: {file_path}")
    else:
        logger.error(f"❌ KHÔNG tìm thấy: {file_path}")

try:
    logger.info("🔄 Đang import các module...")
    from model.VPhoBertTaggermaster.vphoberttagger.models import PhoBertSoftmax
    logger.info("✅ Import PhoBertSoftmax thành công")
    
    from model.VPhoBertTaggermaster.vphoberttagger.constant import LABEL_MAPPING
    logger.info("✅ Import LABEL_MAPPING thành công")
    
    from model.VPhoBertTaggermaster.vphoberttagger.helper import normalize_text
    logger.info("✅ Import normalize_text thành công")
    
except ImportError as e:
    logger.error(f"❌ IMPORT ERROR trong file {current_file}:")
    logger.error(f"   Chi tiết lỗi: {str(e)}")
    logger.error(f"   Traceback:")
    traceback.print_exc()
    logger.error(f"🔧 Cần kiểm tra:")
    logger.error(f"   1. Đường dẫn sys.path: {sys.path[:3]}...")
    logger.error(f"   2. Cấu trúc thư mục vphoberttagger/")
    logger.error(f"   3. Các file .py trong vphoberttagger/")
    sys.exit(1)
except Exception as e:
    logger.error(f"❌ LỖI KHÁC khi import trong file {current_file}:")
    logger.error(f"   Chi tiết: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

# Global variables
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = None
tokenizer = None
id2label = None

def load_model():
    """Load model và tokenizer một lần duy nhất"""
    global model, tokenizer, id2label
    
    if model is not None:
        logger.info("✅ Model đã được load trước đó")
        return True
    
    try:
        # Đường dẫn tới model
        model_path = current_dir / "outputs" / "best_model.pt"
        phobert_path = current_dir / "models" / "phobert-base-v2"
        
        logger.info(f"🔍 Tìm kiếm model tại: {model_path}")
        logger.info(f"🔍 Tìm kiếm PhoBERT tại: {phobert_path}")
        
        if not model_path.exists():
            logger.error(f"❌ FILE NOT FOUND - Model file trong {current_file}:")
            logger.error(f"   Đường dẫn: {model_path}")
            logger.error(f"   Thư mục outputs tồn tại: {model_path.parent.exists()}")
            if model_path.parent.exists():
                logger.error(f"   Các file trong outputs/: {list(model_path.parent.glob('*'))}")
            return False
            
        if not phobert_path.exists():
            logger.error(f"❌ FOLDER NOT FOUND - PhoBERT folder trong {current_file}:")
            logger.error(f"   Đường dẫn: {phobert_path}")
            logger.error(f"   Thư mục models tồn tại: {phobert_path.parent.exists()}")
            if phobert_path.parent.exists():
                logger.error(f"   Các thư mục trong models/: {list(phobert_path.parent.glob('*'))}")
            return False
        
        logger.info(f"🔄 Đang load checkpoint từ: {model_path}")
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        
        # Kiểm tra checkpoint
        if 'args' not in checkpoint:
            logger.error(f"❌ CHECKPOINT ERROR trong {current_file}:")
            logger.error(f"   Checkpoint không có 'args'")
            logger.error(f"   Các keys trong checkpoint: {list(checkpoint.keys())}")
            return False
        
        if 'model' not in checkpoint:
            logger.error(f"❌ CHECKPOINT ERROR trong {current_file}:")
            logger.error(f"   Checkpoint không có 'model'")
            logger.error(f"   Các keys trong checkpoint: {list(checkpoint.keys())}")
            return False
            
        args = checkpoint['args']
        args.model_name_or_path = str(phobert_path)
        
        # Kiểm tra args
        if not hasattr(args, 'label2id'):
            logger.error(f"❌ ARGS ERROR trong {current_file}:")
            logger.error(f"   args không có 'label2id'")
            logger.error(f"   Các thuộc tính trong args: {dir(args)}")
            return False
        
        if not hasattr(args, 'id2label'):
            logger.error(f"❌ ARGS ERROR trong {current_file}:")
            logger.error(f"   args không có 'id2label'")
            return False
        
        logger.info(f"🔄 Đang load AutoConfig...")
        config = AutoConfig.from_pretrained(args.model_name_or_path, num_labels=len(args.label2id))
        
        logger.info(f"🔄 Đang khởi tạo model...")
        model = PhoBertSoftmax(config=config)
        
        logger.info(f"🔄 Đang load state dict...")
        model.load_state_dict(checkpoint['model'], strict=False)
        model.to(device)
        model.eval()
        
        logger.info(f"🔄 Đang load tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path, use_fast=False)
        
        # Load label mapping
        id2label = args.id2label
        
        logger.info(f"✅ Đã load model thành công trên {device}")
        logger.info(f"✅ Số lượng labels: {len(id2label)}")
        return True
        
    except FileNotFoundError as e:
        logger.error(f"❌ FILE NOT FOUND ERROR trong {current_file}:")
        logger.error(f"   File: {str(e)}")
        return False
    except torch.serialization.pickle.UnpicklingError as e:
        logger.error(f"❌ MODEL LOADING ERROR trong {current_file}:")
        logger.error(f"   Lỗi unpickling: {str(e)}")
        logger.error(f"   File model có thể bị corrupt: {model_path}")
        return False
    except Exception as e:
        logger.error(f"❌ UNEXPECTED ERROR trong {current_file} - load_model():")
        logger.error(f"   Chi tiết: {str(e)}")
        logger.error(f"   Traceback:")
        traceback.print_exc()
        return False

def predict_ner(sentence):
    """Dự đoán NER cho một câu"""
    if not load_model():
        logger.error(f"❌ Không thể load model trong {current_file}")
        return [], []
    
    if not sentence or not sentence.strip():
        logger.warning(f"⚠️ Input rỗng trong {current_file} - predict_ner()")
        return [], []
    
    try:
        logger.debug(f"🔄 Đang predict cho: {sentence[:50]}...")
        
        # Normalize text
        sentence = normalize_text(sentence)
        
        # ✅ FIX: Tokenize với max_length phù hợp
        encoding = tokenizer.encode_plus(
            sentence,
            return_tensors='pt',
            truncation=True,
            max_length=256,  # ✅ Giảm từ 512 xuống 256
            padding=True,  # ✅ Thêm padding cố định
            is_split_into_words=False
        )
        
        input_ids = encoding['input_ids'].to(device)
        attention_mask = encoding['attention_mask'].to(device)
        
        # ✅ FIX: Tạo valid_ids và label_masks đúng cách
        batch_size, seq_len = input_ids.shape
        valid_ids = torch.ones((batch_size, seq_len), dtype=torch.long).to(device)
        label_masks = attention_mask.clone().to(device)
        
        # ✅ DEBUG: Log kích thước tensor
        logger.debug(f"Input shape: {input_ids.shape}")
        logger.debug(f"Attention mask shape: {attention_mask.shape}")
        logger.debug(f"Valid ids shape: {valid_ids.shape}")
        logger.debug(f"Label masks shape: {label_masks.shape}")
        
        # Predict
        with torch.no_grad():
            output = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                valid_ids=valid_ids,
                label_masks=label_masks
            )
            
            if not hasattr(output, 'tags'):
                logger.error(f"❌ MODEL OUTPUT ERROR trong {current_file}:")
                logger.error(f"   Output không có 'tags' attribute")
                logger.error(f"   Các attributes: {dir(output)}")
                return [], []
            
            tag_ids = output.tags
        
        # ✅ FIX: Chỉ lấy tokens không phải special tokens
        tokens = tokenizer.convert_ids_to_tokens(input_ids[0])
        
        # ✅ FIX: Kiểm tra length mismatch
        if len(tag_ids) != len(tokens):
            logger.error(f"❌ LENGTH MISMATCH ERROR trong {current_file}:")
            logger.error(f"   Tokens length: {len(tokens)}")
            logger.error(f"   Tag_ids length: {len(tag_ids)}")
            # Cắt cho bằng nhau
            min_len = min(len(tokens), len(tag_ids))
            tokens = tokens[:min_len]
            tag_ids = tag_ids[:min_len]
        
        # ✅ FIX: Kiểm tra tag_ids có nằm trong phạm vi không
        valid_tag_ids = []
        for tag_id in tag_ids:
            if tag_id in id2label:
                valid_tag_ids.append(tag_id)
            else:
                logger.warning(f"⚠️ Tag ID {tag_id} không có trong id2label")
                valid_tag_ids.append(0)  # Mặc định là 'O'
        
        labels = [id2label[tag] for tag in valid_tag_ids]
        
        logger.debug(f"✅ Predict thành công: {len(tokens)} tokens")
        return tokens, labels
        
    except KeyError as e:
        logger.error(f"❌ LABEL MAPPING ERROR trong {current_file} - predict_ner():")
        logger.error(f"   Không tìm thấy label ID: {str(e)}")
        logger.error(f"   Available label IDs: {list(id2label.keys())}")
        return [], []
    except RuntimeError as e:
        logger.error(f"❌ TORCH/CUDA ERROR trong {current_file} - predict_ner():")
        logger.error(f"   Chi tiết: {str(e)}")
        return [], []
    except Exception as e:
        logger.error(f"❌ UNEXPECTED ERROR trong {current_file} - predict_ner():")
        logger.error(f"   Chi tiết: {str(e)}")
        logger.error(f"   Traceback:")
        traceback.print_exc()
        return [], []
    
def extract_entities(tokens, labels):
    """Trích xuất entities từ tokens và labels"""
    if not tokens or not labels:
        logger.warning(f"⚠️ Input rỗng trong {current_file} - extract_entities()")
        return []
    
    if len(tokens) != len(labels):
        logger.error(f"❌ LENGTH MISMATCH trong {current_file} - extract_entities():")
        logger.error(f"   Tokens length: {len(tokens)}")
        logger.error(f"   Labels length: {len(labels)}")
        return []
    
    try:
        entities = []
        current_entity = ''
        current_label = None
        inside_entity = False
        
        for idx, (token, label) in enumerate(zip(tokens, labels)):
            # Skip special tokens
            if token in ['<s>', '</s>', '<pad>', '[PAD]', '[CLS]', '[SEP]']:
                continue
            
            # Clean token
            clean_token = token.replace('@@', '')
            
            if label.startswith('B-'):
                # Lưu entity trước đó nếu có
                if current_entity and current_entity.strip():
                    # Chỉ lưu entity có ít nhất 2 ký tự
                    if len(current_entity.strip()) >= 2:
                        entities.append((current_entity.strip(), current_label))
                
                # Bắt đầu entity mới
                current_entity = clean_token
                current_label = label[2:]  # Bỏ 'B-'
                inside_entity = True
                
            elif label.startswith('I-') and inside_entity and current_label == label[2:]:
                # Tiếp tục entity hiện tại
                if token.startswith('@@'):
                    current_entity += clean_token
                else:
                    current_entity += ' ' + clean_token
                    
            else:
                # Kết thúc entity
                if current_entity and current_entity.strip():
                    if len(current_entity.strip()) >= 2:
                        entities.append((current_entity.strip(), current_label))
                
                current_entity = ''
                inside_entity = False
                current_label = None
        
        # Lưu entity cuối cùng nếu có
        if current_entity and current_entity.strip():
            if len(current_entity.strip()) >= 2:
                entities.append((current_entity.strip(), current_label))
        
        # Loại bỏ duplicate và sort
        unique_entities = list(set(entities))
        
        logger.debug(f"✅ Trích xuất được {len(unique_entities)} entities")
        return unique_entities
        
    except Exception as e:
        logger.error(f"❌ UNEXPECTED ERROR trong {current_file} - extract_entities():")
        logger.error(f"   Chi tiết: {str(e)}")
        logger.error(f"   Traceback:")
        traceback.print_exc()
        return []

def test_ner(text):
    """Test function để kiểm tra NER"""
    print(f"🔄 Testing trong file: {current_file}")
    print(f"Input: {text}")
    print("-" * 50)
    
    try:
        tokens, labels = predict_ner(text)
        
        if not tokens or not labels:
            print("❌ Không thể predict NER")
            return
        
        print("Tokens và Labels:")
        for token, label in zip(tokens, labels):
            if token not in ['<s>', '</s>', '<pad>', '[PAD]']:
                print(f"{token:15} -> {label}")
        
        print("\nEntities:")
        entities = extract_entities(tokens, labels)
        if entities:
            for entity, label in entities:
                print(f"{entity:20} -> {label}")
        else:
            print("Không tìm thấy entities")
        
        print("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ ERROR trong {current_file} - test_ner():")
        logger.error(f"   Chi tiết: {str(e)}")
        traceback.print_exc()

# Test nếu chạy trực tiếp
if __name__ == "__main__":
    try:
        logger.info(f"🚀 Bắt đầu test NER trong file: {current_file}")
        
        # Test cases
        test_texts = [
            "Nguyễn Văn A là sinh viên tại Đại học Bách khoa Hà Nội",
            "Công ty Apple có trụ sở tại California, Hoa Kỳ",
            "Thành phố Hồ Chí Minh là thành phố lớn nhất Việt Nam"
        ]
        
        for i, text in enumerate(test_texts, 1):
            logger.info(f"📝 Test case {i}/{len(test_texts)}")
            test_ner(text)
            
        logger.info(f"✅ Hoàn thành test trong file: {current_file}")
        
    except Exception as e:
        logger.error(f"❌ MAIN ERROR trong {current_file}:")
        logger.error(f"   Chi tiết: {str(e)}")
        traceback.print_exc()