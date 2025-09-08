## 📁 Dataset Structure

### 1. `data/image/` Folder

The `image/` folder contains **1,671 original JPG images** captured during the experimental process.  
> 📌 A single image may correspond to **multiple annotation entries** based on different viewpoints, steps, or anomaly conditions.

---
### 2. `data/mask_groundtruth/` Folder
Ground-truth masks are generated directly from the annotated regions of interest.



---
### 3. `data/annotation/` Folder

The `annotation/annotation.json` file contains all structured annotations for the dataset.  
Each entry corresponds to a specific inspection instance and includes both contextual and visual anomaly information.

Below is an explanation of each field in the annotation records:

| **Key**                  | **Description**                                                                 |
|--------------------------|---------------------------------------------------------------------------------|
| `Image_Id`               | Relative file path to the associated image id.                                     |
| `Stage_Description`      | Describes the experimental operation performed in the current step.             |
| `step`                   | Workflow step identifier (e.g., `"step23"`).                                    |
| `phase`                  | Indicates whether the inspection occurs before (`pre`) or after (`post`) step. |
| `Operator`               | Name of the executing robot, human or agent for the operation.                         |
| `Obj`                    | Target object involved in the step (e.g., silicone container, test tube).       |
| `Start_Position`         | Initial position of the object before manipulation.                             |
| `Dest_Position`          | Destination position where the object is to be placed.                          |
| `Checktype`              | Type of inspection performed (typically `"vision inspection"`).                 |
| `CheckDev`               | Inspection device and its mounting location (e.g., `"Realsense455 on fix_arm"`).|
| `Detection_Location`     | Physical location where the inspection is conducted.                            |
| `Detection_Content`      | Task-specific description of what is being checked.                             |
| `Views`                  | Camera viewpoint relative to the detection location(e.g., `"left-down view"`).                       |
| `Distance`               | Distance between camera and object, labeled `"near"` or `"far"`.  For mobile robot arm, “near” refers to approximately 30–40 cm and “far” to 60–70 cm; for fixed robot arm, “near” refers to 30–40 cm and “far” to 50–60 cm.              |
| `Anomaly_Label`          | Boolean flag indicating whether an anomaly is present (`true` / `false`).       |
| `Anomaly_Type`           | Type of anomaly (e.g., `"Missing"`, `"Inoperable Object"`).                     |
| `Anomaly_Label_Description` | Natural language explanation of the anomaly.                                 |
| `Caption`                | Caption describing the region of interest content in the image.                           |
| `Grounding`              | A list of bounding boxes and labels for the region of interest.                       |
| `Grounding[].text_span`  | A label for the annotated region (e.g., `"Abnormal region""Normal region""test tube""silicone container"`).                   |
| `Grounding[].bbox`       | Bounding box coordinates for the region of interest or object `[xmin, ymin, xmax, ymax]`.                                    |
| `Grounding[].category`   | The anomaly category or object for the bounding box (same as `Anomaly_Type`or`object`).             |
| `conversation`            |  ground-truth dialogues in a human-prompt/GPT-answer style.  Use for VQA benchmark.      |


---


---

### 4. `data/glossary.json`: Vocabulary Glossary

The `glossary.json` file provides standardized definitions of terms used throughout the annotation files. It ensures consistent semantic labeling across the dataset by unifying the vocabulary for objects, positions, and device names.

---

### 5. `data/metasteps.json`: Meta-step Descriptions

The `metasteps.json` file contains the high-level definition of each of the 27 meta-steps defined prior to data acquisition. Each meta-step specifies:

- `operator`: The robot executing the task (e.g., fixed robot arm).
- `obj`: The target object to be manipulated.
- `start_position`: The initial location of the object.
- `dest_position`: The target location to place the object.
- `subtask`: A concise natural language description of the full robotic operation.

Each meta-step also includes optional pre-condition inspection settings:
- `preCheckType`: Type of pre-task inspection (e.g., vision inspection).
- `preCheckDev`: The device used for inspection (e.g., fixed or mobile robot arm with camera).
- `preCheckLocation`: Where the inspection occurs.
- `preCheckContent`: What the inspection checks for.

The `preCheckRes` field lists both `normal` and `abnormal` visual conditions. Each entry includes:
- `description`: A textual explanation of the visual observation.
- `type` (for abnormal entries): The corresponding anomaly type (e.g., Missing, Inoperable Object).
- `caption`: A short image-grounded description used for captioning or grounding tasks.

This file provides the contextual backbone for interpreting image-text annotations and supports reasoning tasks such as anomaly classification and grounded captioning.

---

### 6. `vad/` Folder: Context-Aware Visual Anomaly Detection and Evaluation Code

The `vad` directory contains implementation code for context-aware visual anomaly detection (VAD). It supports:

- Multi-level prompt-based reasoning using image-text pairs
- Hierarchical prompt configuration (e.g., experiment context, step description, detection objective, anomaly description)
- Visual anomaly classification and grounded captioning
- Statistical evaluation and result analysis

This code enables users to benchmark different visual-language models on the dataset and to reproduce detection experiments with customizable settings.

---
### 7. `scripts/` Folder: Annotation Pipeline and Analysis Tools

The `scripts` directory contains:

- Annotation generation program that convert `metasteps.json` and image into the final `annotations.json` format
- Utility scripts for statistical analysis and visualization of the dataset (e.g., anomaly distribution, viewpoint analysis)
- CLIPScore computation code for evaluating image-text relevance

These tools support efficient dataset construction, validation, and downstream performance benchmarking.

---
### 8. `cls/` Folder: good/bad split
In line with common practice (e.g., VisA\MVTec), we offer an explicit “good” and “bad” partition of the datasets, and ground-truth masks are generated directly from the annotated regions of interest.


---

---


## Experimental protocols with anomaly detection

(i) Zero-shot (ZS–All): no parameter learning; evaluate across all viewpoints and distances using textual prompts only, reporting per-view/per-distance metrics and image-level/pixel-level averages. 
(ii) Few-shot (FS–k): for each sampling scene, use k(e.g., k=1,2) positive samples per view for model/prompt calibration references; evaluate across all viewpoints and distances to assess the benefits of limited supervision.
(iii) Leave-One-View-Out (LOVO, distance-agnostic): for each view, calibrate on the other 13 views; assess cross-view generalization.
(iv) Extreme-View OOD: designate space-limited/rare angles (e.g., right-90 downward, left-90 horizontal, right-90 horizontal) as out-of-distribution test sets; calibrate on conventional views only to stress-test robustness to rare/occluded perspectives. 

For all protocols we report Accuracy, Precision, Recall, and F1. If a probabilistic model is used, AUROC and AUPR can be reported as additional metrics; for segmentation tasks, pixel-level pAUROC and PRO may also be included.
To directly support VQA-style evaluation, we added a conversation field to annotation.json, constructing ground-truth dialogues in a human-prompt/GPT-answer style. This is also a kind of experimental protocol.
## Some reproduce methods
### winclip
one-class：thr=0.500000  Acc=38.26  P=100.00  R=1.08  F1=2.13

### AnomalyCLIP
thr=0.500000  Acc=62.91  P=63.92  R=96.47  F1=76.89				

### Anomaly-OV
（without finetune model）Acc=0.38  P=0.80  R=0.04 F1=0.07
（with lora） Acc=0.38  P=0.77  R=0.05 F1=0.10

### Triad
Acc=0.46  P=0.62  R=0.40 F1=0.49