import React, { Component } from 'react'
import PropTypes from 'prop-types'
import update from 'immutability-helper'

import PropertySelector from './General/PropertySelector.js'
import DependencySelector from './SosModel/DependencySelector.js'
import PropertyList from './General/PropertyList.js'

class SosModelConfigForm extends Component {
    constructor(props) {
        super(props)

        this.handleKeyPress = this.handleKeyPress.bind(this)
        this.handleChange = this.handleChange.bind(this)
        this.handleSave = this.handleSave.bind(this)
        this.handleCancel = this.handleCancel.bind(this)

        this.state = {}
        this.state.selectedSosModel = this.props.sosModel
    }

    componentDidMount(){
        document.addEventListener("keydown", this.handleKeyPress, false)
    }

    componentWillUnmount(){
        document.removeEventListener("keydown", this.handleKeyPress, false)
    }

    handleKeyPress(){
        if(event.keyCode === 27) {
            this.handleCancel()
        }
    }

    handleChange(event) {
        const target = event.target
        const value = target.type === 'checkbox' ? target.checked : target.value
        const name = target.name

        this.setState({
            selectedSosModel: update(this.state.selectedSosModel, {[name]: {$set: value}})
        })
    }

    handleSave() {
        this.props.saveSosModel(this.state.selectedSosModel)
    }

    handleCancel() {
        this.props.cancelSosModel()
    }

    render() {
        const {sectorModels, scenarioSets, narrativeSets} = this.props
        const {selectedSosModel} = this.state

        return (
            <div>
                <form>
                    <div className="card">
                        <div className="card-header">General</div>
                        <div className="card-body">

                            <div className="form-group row">
                                <label className="col-sm-2 col-form-label">Name</label>
                                <div className="col-sm-10">
                                    <input className="form-control" name="name" type="text" disabled="true" defaultValue={selectedSosModel.name} onChange={this.handleChange}/>
                                </div>
                            </div>

                            <div className="form-group row">
                                <label className="col-sm-2 col-form-label">Description</label>
                                <div className="col-sm-10">
                                    <textarea className="form-control" name="description" rows="5" defaultValue={selectedSosModel.description} onChange={this.handleChange}/>
                                </div>
                            </div>

                        </div>
                    </div>

                    <br/>

                    <div className="card">
                        <div className="card-header">Settings</div>
                        <div className="card-body">

                            <div className="form-group row">
                                <label className="col-sm-2 col-form-label">Sector Models</label>
                                <div className="col-sm-10">
                                    <PropertySelector name="sector_models" activeProperties={selectedSosModel.sector_models} availableProperties={sectorModels} onChange={this.handleChange} />
                                </div>
                            </div>

                            <div className="form-group row">
                                <label className="col-sm-2 col-form-label">Scenario Sets</label>
                                <div className="col-sm-10">
                                    <PropertySelector name="scenario_sets" activeProperties={selectedSosModel.scenario_sets} availableProperties={scenarioSets} onChange={this.handleChange} />
                                </div>
                            </div>

                            <div className="form-group row">
                                <label className="col-sm-2 col-form-label">Narrative Sets</label>
                                <div className="col-sm-10">
                                    <PropertySelector name="narrative_sets" activeProperties={selectedSosModel.narrative_sets} availableProperties={narrativeSets} onChange={this.handleChange} />
                                </div>
                            </div>
                        </div>
                    </div>

                    <br/>

                    <div className="card">
                        <div className="card-header">Dependencies</div>
                        <div className="card-body">
                            <PropertyList itemsName="dependencies" items={selectedSosModel.dependencies} columns={{source_model: 'Source Model', source_model_output: 'Output', sink_model: 'Sink Model', sink_model_input: 'Input'}} editButton={false} deleteButton={true} onDelete={this.handleChange} />
                            <DependencySelector dependencies={selectedSosModel.dependencies} sectorModels={sectorModels} onChange={this.handleChange}/>
                        </div>
                    </div>

                    <br/>

                    <div className="card">
                        <div className="card-header">Iteration Settings</div>
                        <div className="card-body">
                            <div className="form-group row">
                                <label className="col-sm-2 col-form-label">Maximum Iterations</label>
                                <div className="col-sm-10">
                                    <input className="form-control" name="max_iterations" type="number" min="1" defaultValue={selectedSosModel.max_iterations} onChange={this.handleChange}/>
                                </div>
                            </div>

                            <div className="form-group row">
                                <label className="col-sm-2 col-form-label">Absolute Convergence Tolerance</label>
                                <div className="col-sm-10">
                                    <input className="form-control" name="convergence_absolute_tolerance" type="number" step="0.00000001" min="0.00000001" defaultValue={selectedSosModel.convergence_absolute_tolerance} onChange={this.handleChange}/>
                                </div>
                            </div>
                            <div className="form-group row">
                                <label className="col-sm-2 col-form-label">Relative Convergence Tolerance</label>
                                <div className="col-sm-10">
                                    <input className="form-control" name="convergence_relative_tolerance" type="number" step="0.00000001" min="0.00000001" defaultValue={selectedSosModel.convergence_relative_tolerance} onChange={this.handleChange}/>
                                </div>
                            </div>
                        </div>
                    </div>

                    <br/>
                </form>

                <input className="btn btn-secondary btn-lg btn-block" type="button" value="Save System-of-systems Model Configuration" onClick={this.handleSave} />
                <input className="btn btn-secondary btn-lg btn-block" type="button" value="Cancel" onClick={this.handleCancel} />

                <br/>
            </div>
        )
    }
}

SosModelConfigForm.propTypes = {
    sosModel: PropTypes.object.isRequired,
    sectorModels: PropTypes.array.isRequired,
    scenarioSets: PropTypes.array.isRequired,
    narrativeSets: PropTypes.array.isRequired,
    saveSosModel: PropTypes.func.isRequired,
    cancelSosModel: PropTypes.func.isRequired
}

export default SosModelConfigForm