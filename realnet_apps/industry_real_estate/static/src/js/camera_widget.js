/** @odoo-module **/

import { Component, useRef, onMounted, reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class CameraWidget extends Component {
    static template = "industry_real_estate.CameraWidget";
    static props = { ...standardFieldProps };

    setup() {
        //Definición de variables, usos y estados
        this.mediaRecorder = null;
        this.chunks = [];
        this.recordingTimeout = null;
        this.estadoCamara = "cerrado";

        this.videoRef = useRef("video");
        this.btnOpenCamera = useRef("btnOpenCamera");
        this.btnRecordCamera = useRef("btnRecordCamera");
        this.btnSaveImage = useRef("btnSaveImage");
        this.btnCloseCamera = useRef("btnCloseCamera");

        this.notification = useService("notification");
        //validación de edición
        this.isEditMode = !!this.props.record.resId;
        this.state = reactive({
            photoType: null
        });
        //validación de grabaciones
        if (this.props.record.resId && this.props.record.data.photo) {
            const val = this.props.record.data.photo;
            if (val.startsWith?.("data:video")) {
                this.state.photoType = "video";
            } else if (val.startsWith?.("data:image")) {
                this.state.photoType = "image";
            } else {
                this.state.photoType = "nada";
            }
        }
        // validación de mime
        if (this.props.record.data.photo_mime) {
            const mime = this.props.record.data.photo_mime;
            this.state.photoType = mime.startsWith("video") ? "video"
                                    : mime.startsWith("image") ? "image"
                                    : null;
        }
        // si es modo edición, no se cargarán los controles                    
        if (!this.isEditMode) {
            onMounted(() => {
                this.actualizarControles();
            });
        }
    }
    //funcionalidad de controles
    actualizarControles() {
        const display = (el, show) => {
            if (el?.el) el.el.style.display = show ? "inline" : "none";
        };

        display(this.btnOpenCamera, this.estadoCamara === "cerrado");
        display(this.btnSaveImage, this.estadoCamara !== "cerrado");
        display(this.btnCloseCamera, this.estadoCamara !== "cerrado");
        display(this.btnRecordCamera, this.estadoCamara === "abierto");
    }
    //apertura de cámara
    async openCamera() {
        try {
            this.estadoCamara = "abierto";
            this.stream = await navigator.mediaDevices.getUserMedia({ video: true });
            if (this.videoRef?.el) {
                this.videoRef.el.srcObject = this.stream;
            }
            this.actualizarControles();
        } catch (err) {
            console.error("Error al acceder a la cámara:", err);
        }
    }
    //cerrar cámara
    async closeCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
        if (this.videoRef?.el) {
            this.videoRef.el.srcObject = null;
        }
        this.stream = null;
        this.estadoCamara = "cerrado";
        this.actualizarControles();
    }
    //iniciar grabación
    startRecording() {
        if (!this.stream) return;

        this.estadoCamara = "grabando";
        this.actualizarControles();
        this.chunks = [];

        this.mediaRecorder = new MediaRecorder(this.stream, { mimeType: "video/webm" });

        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                this.chunks.push(e.data);
            }
        };

        this.mediaRecorder.onstop = () => {
            const blob = new Blob(this.chunks, { type: "video/webm" });
            const reader = new FileReader();

            reader.onloadend = () => {
                const base64Data = reader.result.split(",")[1];

                const previewField = this.props.name === 'x_camera_placeholder'
                    ? 'x_camera_preview_entrada'
                    : this.props.name === 'x_camera_recepcion'
                    ? 'x_camera_preview_recepcion'
                    : null;

                const updateData = { 
                    [this.props.name]: base64Data, 
                    photo_mime: "video/webm",
                };
                if (previewField) {
                    updateData[previewField] = base64Data;
                }
                this.state.photoType = "video";
                this.props.record.update(updateData);
                this.notification.add("Video grabado y guardado", { type: "success" });
            };

            reader.readAsDataURL(blob);
        };

        this.mediaRecorder.start();
        this.notification.add("Grabación iniciada (1 min máx)", { type: "info" });

        this.recordingTimeout = setTimeout(() => this.stopRecording(), 60000);
    }
    //parar grabación
    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
            this.mediaRecorder.stop();
        }
        if (this.recordingTimeout) {
            clearTimeout(this.recordingTimeout);
            this.recordingTimeout = null;
        }
        this.closeCamera();
    }
    //salvar capturas y videos
    async captureAndSave() {
        if (this.videoRef.el && this.videoRef.el.srcObject) {
            const canvas = document.createElement("canvas");
            canvas.width = this.videoRef.el.videoWidth;
            canvas.height = this.videoRef.el.videoHeight;

            const ctx = canvas.getContext("2d");
            ctx.drawImage(this.videoRef.el, 0, 0, canvas.width, canvas.height);

            const base64Data = canvas.toDataURL("image/png").split(",")[1];

            const previewField = this.props.name === 'x_camera_placeholder'
                ? 'x_camera_preview_entrada'
                : this.props.name === 'x_camera_recepcion'
                ? 'x_camera_preview_recepcion'
                : null;

            const updateData = { 
                [this.props.name]: base64Data, 
                photo_mime: "image/png", 
            };
            if (previewField) {
                updateData[previewField] = base64Data;
            }
            this.state.photoType = "image";
            this.props.record.update(updateData);
            this.notification.add("Imagen capturada y guardada", { type: "success" });
            this.closeCamera();
        }
    }
}
//registrar el componente
registry.category("fields").add("camera_widget", {
    component: CameraWidget,
    displayName: "Camera Widget",
    supportedTypes: ["binary"],
});
